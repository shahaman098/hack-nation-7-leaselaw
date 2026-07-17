from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from hackforge.providers import LLMProvider, LLMResponse, ProviderConfigurationError

_SUPPORTED_MODELS = {"deepseek-v4-pro", "deepseek-v4-flash"}
_CONSERVATIVE_PRICING_PER_MILLION = {
    "deepseek-v4-pro": (0.435, 0.87),
    "deepseek-v4-flash": (0.14, 0.28),
}
_MAX_REASONING_MARKERS = (
    "blind hackathon judge",
    "red-team critic",
)
_GENERATION_MARKERS = (
    "opportunity-card-generator",
    "mechanism-mining",
    "concept-crossing-engine",
    "reflective-mutation-engine",
)
_CONSTRAINED_REVIEW_MARKERS = (
    "collision auditor",
    "feasibility reviewer",
)
_CONSTRAINED_JUDGE_MARKERS = ("blind hackathon judge",)


class _DeepSeekTransientError(RuntimeError):
    """A retryable transport or server-side DeepSeek failure."""


class DeepSeekProvider(LLMProvider):
    """Direct, single-model DeepSeek V4 client with no provider fallback."""

    name = "deepseek"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        api_base: str | None = None,
        reasoning_profile: str | None = None,
        client: httpx.Client | None = None,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            raise ProviderConfigurationError(
                "DEEPSEEK_API_KEY is not set. DeepSeek is the default provider, and no Codex or "
                "alternate-model fallback was attempted."
            )

        requested_model = model or os.getenv("HACKFORGE_DEEPSEEK_MODEL") or "deepseek-v4-pro"
        self.requested_model = requested_model.removeprefix("deepseek/")
        if self.requested_model not in _SUPPORTED_MODELS:
            supported = ", ".join(sorted(_SUPPORTED_MODELS))
            raise ProviderConfigurationError(
                f"Unsupported DeepSeek model {self.requested_model!r}; choose one of: {supported}. "
                "No model fallback was attempted."
            )
        self.model = self.requested_model

        self.reasoning_profile = (
            reasoning_profile or os.getenv("HACKFORGE_DEEPSEEK_REASONING") or "adaptive"
        ).lower()
        if self.reasoning_profile not in {"adaptive", "high", "max"}:
            raise ProviderConfigurationError(
                "HACKFORGE_DEEPSEEK_REASONING must be adaptive, high, or max. "
                "No default/fallback profile was substituted."
            )

        self.api_base = (
            api_base or os.getenv("HACKFORGE_DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        ).rstrip("/")
        self.timeout = float(os.getenv("HACKFORGE_LLM_TIMEOUT", "90"))
        self.stream_timeout = self._positive_float("HACKFORGE_STREAM_TIMEOUT", 300.0)
        self.max_tokens = int(os.getenv("HACKFORGE_DEEPSEEK_MAX_TOKENS", "16384"))
        if self.max_tokens < 1:
            raise ProviderConfigurationError("HACKFORGE_DEEPSEEK_MAX_TOKENS must be positive")
        self.constrained_max_tokens = self._positive_int(
            "HACKFORGE_DEEPSEEK_CONSTRAINED_MAX_TOKENS", 4096
        )
        self.judging_max_tokens = self._positive_int("HACKFORGE_DEEPSEEK_JUDGING_MAX_TOKENS", 4096)
        self.max_calls = self._positive_int("HACKFORGE_MAX_LLM_CALLS", 40)
        self.max_total_tokens = self._positive_int("HACKFORGE_MAX_TOTAL_TOKENS", 750_000)
        self.max_cost_usd = self._positive_float("HACKFORGE_MAX_COST_USD", 2.0)
        default_input_price, default_output_price = _CONSERVATIVE_PRICING_PER_MILLION[self.model]
        self.input_price_per_million = self._positive_float(
            "HACKFORGE_DEEPSEEK_INPUT_USD_PER_MILLION", default_input_price
        )
        self.output_price_per_million = self._positive_float(
            "HACKFORGE_DEEPSEEK_OUTPUT_USD_PER_MILLION", default_output_price
        )
        self._usage_lock = threading.Lock()
        self._attempted_calls = 0
        self._completed_calls = 0
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._estimated_cost_usd = 0.0
        self._client = client

    def complete(self, system: str, user: str, *, temperature: float = 0.4) -> LLMResponse:
        # DeepSeek ignores sampling parameters in thinking mode, so do not send a fake control.
        del temperature
        effort = self._reasoning_effort(system)
        thinking_enabled = self._thinking_enabled(system)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "thinking": {"type": "enabled" if thinking_enabled else "disabled"},
            "max_tokens": self._max_tokens_for(system),
            # Thinking-mode responses can take longer than a normal HTTP read
            # timeout before their final JSON arrives. Streaming reasoning
            # chunks keeps the connection active without exposing CoT in any
            # artifact; only the final content is returned to callers.
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if thinking_enabled:
            payload["reasoning_effort"] = effort
        data = self._request(payload)
        try:
            choice = data["choices"][0]
            text = choice["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise _DeepSeekTransientError(
                f"DeepSeek returned an invalid completion payload: {self._safe_detail(data)}"
            ) from exc
        if not isinstance(text, str) or not text.strip():
            raise _DeepSeekTransientError("DeepSeek returned an empty final answer")

        usage = data.get("usage")
        if not isinstance(usage, dict):  # _request enforces this; keep the response boundary typed.
            raise RuntimeError("DeepSeek response lost usage accounting after validation")
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw={
                "id": data.get("id") if isinstance(data, dict) else None,
                "thinking": "enabled" if thinking_enabled else "disabled",
                "reasoning_effort": effort if thinking_enabled else None,
            },
        )

    def probe(self) -> dict[str, Any]:
        """Make a tiny real chat request to validate auth, model access, and available balance."""
        data = self._request(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Return exactly READY."},
                    {"role": "user", "content": "Readiness probe"},
                ],
                "thinking": {"type": "disabled"},
                "max_tokens": 16,
                "stream": False,
            }
        )
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"DeepSeek readiness probe returned an invalid payload: {data!r}") from exc
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("DeepSeek readiness probe returned an empty response")
        return {"model": self.model, "response_id": data.get("id"), "ok": True}

    def usage_snapshot(self) -> dict[str, Any]:
        with self._usage_lock:
            return {
                "attempted_calls": self._attempted_calls,
                "completed_calls": self._completed_calls,
                "prompt_tokens": self._prompt_tokens,
                "completion_tokens": self._completion_tokens,
                "total_tokens": self._prompt_tokens + self._completion_tokens,
                "estimated_cost_usd": round(self._estimated_cost_usd, 6),
                "budget": {
                    "max_calls": self.max_calls,
                    "max_total_tokens": self.max_total_tokens,
                    "max_cost_usd": self.max_cost_usd,
                },
                "pricing_per_million": {
                    "input_usd": self.input_price_per_million,
                    "output_usd": self.output_price_per_million,
                    "method": "conservative: all prompt tokens priced as cache misses",
                },
            }

    def _reserve_call(self) -> None:
        with self._usage_lock:
            if self._attempted_calls >= self.max_calls:
                raise RuntimeError(
                    f"LLM call budget exhausted ({self._attempted_calls}/{self.max_calls}); "
                    "no additional request was sent"
                )
            self._attempted_calls += 1

    def _record_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        with self._usage_lock:
            self._completed_calls += 1
            self._prompt_tokens += prompt_tokens
            self._completion_tokens += completion_tokens
            self._estimated_cost_usd += (
                prompt_tokens * self.input_price_per_million
                + completion_tokens * self.output_price_per_million
            ) / 1_000_000
            total_tokens = self._prompt_tokens + self._completion_tokens
            if total_tokens > self.max_total_tokens:
                raise RuntimeError(
                    f"LLM token budget exceeded ({total_tokens}/{self.max_total_tokens}); run stopped"
                )
            if self._estimated_cost_usd > self.max_cost_usd:
                raise RuntimeError(
                    f"LLM cost budget exceeded (${self._estimated_cost_usd:.4f}/${self.max_cost_usd:.4f}); "
                    "run stopped"
                )

    @staticmethod
    def _positive_int(name: str, default: int) -> int:
        try:
            value = int(os.getenv(name, str(default)))
        except ValueError as exc:
            raise ProviderConfigurationError(f"{name} must be a positive integer") from exc
        if value < 1:
            raise ProviderConfigurationError(f"{name} must be a positive integer")
        return value

    @staticmethod
    def _positive_float(name: str, default: float) -> float:
        try:
            value = float(os.getenv(name, str(default)))
        except ValueError as exc:
            raise ProviderConfigurationError(f"{name} must be a positive number") from exc
        if value <= 0:
            raise ProviderConfigurationError(f"{name} must be a positive number")
        return value

    def _reasoning_effort(self, system: str) -> str:
        if self.reasoning_profile in {"high", "max"}:
            return self.reasoning_profile
        normalized = system.lower()
        return "max" if any(marker in normalized for marker in _MAX_REASONING_MARKERS) else "high"

    def _max_tokens_for(self, system: str) -> int:
        normalized = system.lower()
        if any(marker in normalized for marker in _MAX_REASONING_MARKERS):
            return min(self.max_tokens, self.judging_max_tokens)
        if any(marker in normalized for marker in _CONSTRAINED_REVIEW_MARKERS):
            return min(self.max_tokens, self.constrained_max_tokens)
        return self.max_tokens

    @staticmethod
    def _thinking_enabled(system: str) -> bool:
        """Use fast constrained decoding where a fixed schema bounds the task.

        These stages produce many schema-checked alternatives which are then
        evidence-gated and independently reviewed. Collision and feasibility
        reviews also operate over retrieved evidence with compact, fixed output
        schemas, so hidden reasoning adds disproportionate latency there.
        Final judging and red-team stages keep reasoning enabled. Set
        HACKFORGE_DEEPSEEK_GENERATION_THINKING=1 or
        HACKFORGE_DEEPSEEK_REVIEW_THINKING=1 to opt back in.
        """
        enabled_values = {
            "1",
            "true",
            "yes",
            "on",
        }
        normalized = system.lower()
        if any(marker in normalized for marker in _GENERATION_MARKERS):
            return os.getenv("HACKFORGE_DEEPSEEK_GENERATION_THINKING", "0").strip().lower() in enabled_values
        if any(marker in normalized for marker in _CONSTRAINED_REVIEW_MARKERS):
            return os.getenv("HACKFORGE_DEEPSEEK_REVIEW_THINKING", "0").strip().lower() in enabled_values
        if (
            any(marker in normalized for marker in _CONSTRAINED_JUDGE_MARKERS)
            and "pairwise-comparator" not in normalized
        ):
            return os.getenv("HACKFORGE_DEEPSEEK_JUDGE_VOTE_THINKING", "0").strip().lower() in enabled_values
        return True

    def _stream_deadline(self) -> float:
        """Bound a streaming response even when reasoning chunks keep arriving."""
        return time.monotonic() + self.stream_timeout

    def _stream_timed_out(self, deadline: float) -> bool:
        return time.monotonic() > deadline

    @retry(
        reraise=True,
        retry=retry_if_exception_type(_DeepSeekTransientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=20),
    )
    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Count actual HTTP attempts, including same-model retries. This is the
        # enforceable unit for both rate and spend controls.
        self._reserve_call()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            if payload.get("stream"):
                return self._request_streaming(payload, headers)
            if self._client is not None:
                response = self._client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.api_base}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
        except httpx.HTTPError as exc:
            raise _DeepSeekTransientError(f"DeepSeek transport failed: {exc}") from exc

        if response.status_code >= 400:
            message = self._safe_detail(response)
            detail = f"DeepSeek request failed with HTTP {response.status_code}: {message}"
            if response.status_code in {400, 401, 402, 403, 404, 405, 422}:
                raise ProviderConfigurationError(f"{detail}. No provider or model fallback was attempted.")
            raise _DeepSeekTransientError(detail)
        try:
            data = response.json()
        except ValueError as exc:
            raise _DeepSeekTransientError(
                f"DeepSeek returned non-JSON HTTP {response.status_code}: {response.text[:1000]}"
            ) from exc
        if not isinstance(data, dict):
            raise _DeepSeekTransientError(f"DeepSeek returned a non-object payload: {data!r}")
        usage = data.get("usage")
        if not isinstance(usage, dict):
            raise RuntimeError(
                "DeepSeek response omitted usage accounting; token and cost budgets cannot be enforced"
            )
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        if not isinstance(prompt_tokens, int) or not isinstance(completion_tokens, int):
            raise RuntimeError(
                "DeepSeek response returned invalid usage accounting; token and cost budgets cannot be enforced"
            )
        self._record_usage(prompt_tokens, completion_tokens)
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise _DeepSeekTransientError(
                f"DeepSeek returned an invalid completion payload: {self._safe_detail(data)}"
            ) from exc
        if not isinstance(content, str) or not content.strip():
            reasoning = choice.get("message", {}).get("reasoning_content") or ""
            finish_reason = choice.get("finish_reason") or "unknown"
            raise _DeepSeekTransientError(
                "DeepSeek returned an empty final answer "
                f"(finish_reason={finish_reason}, reasoning_chars={len(str(reasoning))}); "
                "retrying the same model without fallback"
            )
        return data

    def _request_streaming(self, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        """Read a DeepSeek SSE completion into the normal completion shape.

        The API emits reasoning chunks before final content. We intentionally
        discard the former and retain the final answer plus final usage block,
        so callers keep the same budget-enforced interface as non-streaming
        requests.
        """
        url = f"{self.api_base}/chat/completions"
        deadline = self._stream_deadline()
        try:
            if self._client is not None:
                with self._client.stream("POST", url, headers=headers, json=payload, timeout=self.timeout) as response:
                    return self._consume_stream(response, deadline=deadline)
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream("POST", url, headers=headers, json=payload) as response:
                    return self._consume_stream(response, deadline=deadline)
        except httpx.HTTPError as exc:
            raise _DeepSeekTransientError(f"DeepSeek transport failed: {exc}") from exc

    def _consume_stream(self, response: httpx.Response, *, deadline: float) -> dict[str, Any]:
        if response.status_code >= 400:
            message = self._safe_detail(response)
            detail = f"DeepSeek request failed with HTTP {response.status_code}: {message}"
            if response.status_code in {400, 401, 402, 403, 404, 405, 422}:
                raise ProviderConfigurationError(f"{detail}. No provider or model fallback was attempted.")
            raise _DeepSeekTransientError(detail)

        content_type = response.headers.get("content-type", "").lower()
        if "text/event-stream" not in content_type:
            # Keeps injected test clients and compatible non-streaming proxies
            # working while production requests use SSE.
            try:
                data = response.json()
            except ValueError as exc:
                raise _DeepSeekTransientError(
                    f"DeepSeek returned non-JSON HTTP {response.status_code}: {response.text[:1000]}"
                ) from exc
            return self._validate_response_data(data)

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        response_id: Any = None
        finish_reason: Any = None
        usage: Any = None
        try:
            for line in response.iter_lines():
                if self._stream_timed_out(deadline):
                    raise _DeepSeekTransientError(
                        f"DeepSeek stream exceeded the configured {self.stream_timeout:g}s total deadline"
                    )
                if not line or not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    break
                event = json.loads(raw)
                if not isinstance(event, dict):
                    continue
                response_id = event.get("id") or response_id
                if isinstance(event.get("usage"), dict):
                    usage = event["usage"]
                choices = event.get("choices") or []
                if not choices or not isinstance(choices[0], dict):
                    continue
                choice = choices[0]
                delta = choice.get("delta") or {}
                if isinstance(delta, dict):
                    content = delta.get("content")
                    reasoning = delta.get("reasoning_content")
                    if isinstance(content, str):
                        content_parts.append(content)
                    if isinstance(reasoning, str):
                        reasoning_parts.append(reasoning)
                finish_reason = choice.get("finish_reason") or finish_reason
        except (ValueError, json.JSONDecodeError) as exc:
            raise _DeepSeekTransientError(f"DeepSeek returned invalid stream data: {exc}") from exc

        return self._validate_response_data(
            {
                "id": response_id,
                "choices": [
                    {
                        "message": {
                            "content": "".join(content_parts),
                            "reasoning_content": "".join(reasoning_parts),
                        },
                        "finish_reason": finish_reason,
                    }
                ],
                "usage": usage,
            }
        )

    def _validate_response_data(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise _DeepSeekTransientError(f"DeepSeek returned a non-object payload: {data!r}")
        usage = data.get("usage")
        if not isinstance(usage, dict):
            raise RuntimeError(
                "DeepSeek response omitted usage accounting; token and cost budgets cannot be enforced"
            )
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        if not isinstance(prompt_tokens, int) or not isinstance(completion_tokens, int):
            raise RuntimeError(
                "DeepSeek response returned invalid usage accounting; token and cost budgets cannot be enforced"
            )
        self._record_usage(prompt_tokens, completion_tokens)
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise _DeepSeekTransientError(
                f"DeepSeek returned an invalid completion payload: {self._safe_detail(data)}"
            ) from exc
        if not isinstance(content, str) or not content.strip():
            reasoning = choice.get("message", {}).get("reasoning_content") or ""
            finish_reason = choice.get("finish_reason") or "unknown"
            raise _DeepSeekTransientError(
                "DeepSeek returned an empty final answer "
                f"(finish_reason={finish_reason}, reasoning_chars={len(str(reasoning))}); "
                "retrying the same model without fallback"
            )
        return data

    @staticmethod
    def _safe_detail(value: Any) -> str:
        if isinstance(value, httpx.Response):
            try:
                value = value.json()
            except ValueError:
                return value.text[:1000] or "empty response body"
        if isinstance(value, dict):
            error = value.get("error")
            if isinstance(error, dict) and error.get("message"):
                return str(error["message"])[:1000]
            return str(value)[:1000]
        return str(value)[:1000]
