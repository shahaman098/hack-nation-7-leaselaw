from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from hackforge.utils import env_flag

_RETRY = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=20),
)


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class ProviderConfigurationError(RuntimeError):
    """A permanent provider/auth/model error that must not consume retries."""


class _CodexTransientError(RuntimeError):
    """A short-lived local Codex CLI, MCP, or network failure."""


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, system: str, user: str, *, temperature: float = 0.4) -> LLMResponse:
        raise NotImplementedError

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.3,
        retries: int = 2,
        schema: dict[str, Any] | None = None,
    ) -> Any:
        """Request JSON, retrying with a stricter instruction if parsing fails."""
        instruction = "\n\nReturn valid JSON only. No markdown fences, no prose."
        if schema:
            instruction += (
                "\nYour response MUST validate against this exact JSON Schema. Use the exact property "
                "names, types, and required fields; do not rename, merge, or add properties:\n"
                + json.dumps(schema, separators=(",", ":"))
            )
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            suffix = instruction
            if attempt > 0 and last_error is not None:
                suffix += (
                    "\n\nYour previous reply failed parsing or schema validation. Correct this exact "
                    f"problem: {str(last_error)[:2000]}\nReply with ONLY the corrected JSON value."
                )
            try:
                resp = self.complete(system + suffix, user, temperature=max(0.0, temperature - 0.1 * attempt))
                parsed = extract_json(resp.text)
                if schema:
                    jsonschema.validate(parsed, schema)
                return parsed
            except (json.JSONDecodeError, ValueError, jsonschema.ValidationError) as exc:
                last_error = exc
        detail = f": {str(last_error)[:500]}" if last_error else ""
        raise ValueError(
            f"{self.name}: could not obtain valid JSON matching the schema after "
            f"{retries + 1} attempts{detail}"
        ) from last_error


def extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try first JSON object/array substring
        for opener, closer in (("{", "}"), ("[", "]")):
            start = text.find(opener)
            end = text.rfind(closer)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    continue
        raise


class DryRunProvider(LLMProvider):
    """Deterministic fixture responses for tests and benchmarks only."""

    name = "dry-run"

    def __init__(self, fixture_bundle: dict[str, Any] | None = None):
        self.fixture_bundle = fixture_bundle or {}
        self.model = "dry-run-v1"
        self.calls: list[dict[str, str]] = []

    def complete(self, system: str, user: str, *, temperature: float = 0.4) -> LLMResponse:
        self.calls.append({"system": system[:200], "user": user[:200]})
        key = self._route_key(system, user)
        payload = self.fixture_bundle.get(key)
        if payload is None:
            raise RuntimeError(f"Test fixture bundle has no response for route {key!r}")
        text = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
        return LLMResponse(text=text, provider=self.name, model=self.model)

    def _route_key(self, system: str, user: str) -> str:
        blob = (system + "\n" + user).lower()
        if "competition build-plan planner" in blob:
            return "build_plan"
        if "develop scaffold call" in blob:
            return "develop_scaffold"
        if "develop task call" in blob:
            return "develop_task"
        if "winner-pattern-analyst" in blob:
            return "winner_patterns"
        if "competition-intelligence" in blob or "do not generate product ideas" in blob:
            return "competition_research"
        if "contrarian product researcher" in blob:
            return "ideation"
        if "opportunity-card-generator" in blob:
            return "opportunity_cards"
        if "mechanism-card-generator" in blob:
            return "mechanism_cards"
        if "concept-crossing-engine" in blob:
            return "idea_crossing"
        if "reflective-mutation-engine" in blob:
            return "mutations"
        if "collision auditor" in blob:
            return "collision"
        if "feasibility reviewer" in blob:
            return "feasibility"
        if "blind hackathon judge" in blob:
            # Extract role if present
            m = re.search(r"role:\s*([a-z\-]+)", blob)
            role = m.group(1) if m else "technical"
            return f"judge_{role}"
        if "red-team critic" in blob:
            return "red_team"
        if "ten winning ideas" in blob or "give me ten" in blob:
            return "baseline_ten"
        return "default"


class CodexExecProvider(LLMProvider):
    """Use the locally authenticated Codex CLI without requiring an API key."""

    name = "codex"

    def __init__(
        self,
        *,
        binary: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        self.binary: str = binary or os.getenv("HACKFORGE_CODEX_BINARY") or shutil.which("codex") or ""
        # ChatGPT-backed Codex accounts do not necessarily expose every API
        # model name. Leave the model flag unset by default so Codex selects the
        # authenticated account's supported default. Set HACKFORGE_CODEX_MODEL
        # only when the account explicitly supports that model.
        self.requested_model: str | None = model or os.getenv("HACKFORGE_CODEX_MODEL") or None
        self.model: str = self.requested_model or "codex-default"
        self.timeout = timeout or float(os.getenv("HACKFORGE_CODEX_TIMEOUT", "300"))
        if not self.binary:
            raise RuntimeError("Codex CLI was not found. Install Codex or choose a configured live provider.")

    def complete(self, system: str, user: str, *, temperature: float = 0.4) -> LLMResponse:
        del temperature  # Codex controls reasoning/search policy for exec sessions.
        return self._execute(system, user, schema=None)

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.3,
        retries: int = 2,
        schema: dict[str, Any] | None = None,
    ) -> Any:
        del temperature
        output_schema = schema
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            suffix = (
                "\nReturn only data conforming to the supplied JSON schema."
                if output_schema
                else "\nReturn one valid JSON object only, with no Markdown or commentary."
            )
            if attempt:
                suffix += " Your last response was invalid; correct the structure without commentary."
            try:
                response = self._execute(system + suffix, user, schema=output_schema)
                parsed = extract_json(response.text)
                if output_schema:
                    jsonschema.validate(parsed, output_schema)
                return parsed
            except ProviderConfigurationError:
                raise
            except _CodexTransientError:
                # The provider boundary already used its bounded transport retry.
                # Do not mislabel an exhausted service failure as malformed JSON.
                raise
            except (ValueError, json.JSONDecodeError, jsonschema.ValidationError) as exc:
                last_error = exc
        raise ValueError(f"codex: invalid structured output after {retries + 1} attempts") from last_error

    def _execute(self, system: str, user: str, *, schema: dict[str, Any] | None) -> LLMResponse:
        for attempt in range(3):
            try:
                return self._execute_once(system, user, schema=schema)
            except _CodexTransientError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
        raise AssertionError("unreachable")

    def _execute_once(self, system: str, user: str, *, schema: dict[str, Any] | None) -> LLMResponse:
        prompt = f"SYSTEM INSTRUCTIONS:\n{system}\n\nTASK:\n{user}"
        with tempfile.TemporaryDirectory(prefix="hackforge-codex-") as temp:
            temp_dir = Path(temp)
            last_path = temp_dir / "last-message.txt"
            command = [
                self.binary,
                "exec",
                # HackForge needs only the authenticated Codex model, not the
                # operator's arbitrary MCP servers. Ignore those project/user
                # integrations while retaining the Codex login in CODEX_HOME.
                "--ignore-user-config",
                "--sandbox",
                "read-only",
                "--ephemeral",
                "--skip-git-repo-check",
                "--json",
                "--output-last-message",
                str(last_path),
            ]
            if self.requested_model:
                command[2:2] = ["--model", self.requested_model]
            if schema:
                schema_path = temp_dir / "output-schema.json"
                schema_path.write_text(json.dumps(_codex_strict_schema(schema)), encoding="utf-8")
                command.extend(["--output-schema", str(schema_path)])
            command.append("-")
            try:
                completed = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout,
                    cwd=temp,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise _CodexTransientError(f"Codex exec timed out after {self.timeout:g}s") from exc
            if completed.returncode != 0:
                stderr = completed.stderr.strip()
                detail = "\n".join(
                    part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
                ) or "unknown Codex error"
                # Stderr is the CLI/runtime diagnostic; stdout may contain an
                # agent response that happens to mention authentication.
                diagnostic = stderr or detail
                if "model is not supported" in diagnostic.lower():
                    raise ProviderConfigurationError(
                        f"Requested Codex model {self.requested_model!r} is not supported by this "
                        f"account. No fallback was attempted. Provider output: {detail[-1000:]}"
                    )
                if _is_codex_auth_failure(diagnostic):
                    raise ProviderConfigurationError(
                        f"Codex authentication is unavailable: {detail[-500:]}"
                    )
                if _is_codex_transient_failure(diagnostic):
                    raise _CodexTransientError(f"Codex exec transient failure: {detail[-2000:]}")
                raise RuntimeError(f"Codex exec failed ({completed.returncode}): {detail[-2000:]}")
            text = last_path.read_text(encoding="utf-8").strip() if last_path.exists() else ""
            if not text:
                text = self._extract_jsonl_message(completed.stdout)
            if not text:
                raise RuntimeError("Codex exec completed without a final message")
            return LLMResponse(
                text=text,
                provider=self.name,
                model=self.model,
                raw={"jsonl": completed.stdout[-4000:]},
            )

    @staticmethod
    def _extract_jsonl_message(stdout: str) -> str:
        candidates: list[str] = []

        def visit(value: Any, key: str = "") -> None:
            if isinstance(value, dict):
                for child_key, child in value.items():
                    visit(child, child_key)
            elif isinstance(value, list):
                for child in value:
                    visit(child, key)
            elif isinstance(value, str) and key in {"text", "content", "message", "output_text"}:
                candidates.append(value)

        for line in stdout.splitlines():
            try:
                visit(json.loads(line))
            except json.JSONDecodeError:
                continue
        for candidate in reversed(candidates):
            try:
                extract_json(candidate)
                return candidate
            except (ValueError, json.JSONDecodeError):
                continue
        return candidates[-1] if candidates else ""


def _is_codex_auth_failure(detail: str) -> bool:
    """Return true only for actionable credential/login failures.

    Codex can mention authentication while reporting a transient MCP transport
    failure during startup or shutdown. Treating every ``auth`` substring as a
    permanent configuration fault bypasses ``complete_json``'s bounded retry
    loop and needlessly aborts long-running searches.
    """
    text = detail.lower()
    markers = (
        "not logged in",
        "authentication required",
        "login required",
        "please log in",
        "please login",
        "run `codex login`",
        "run codex login",
        "invalid api key",
        "invalid credentials",
        "unauthorized (401)",
        "http 401",
        "status code: 401",
    )
    return any(marker in text for marker in markers)


def _is_codex_transient_failure(detail: str) -> bool:
    """Recognize transient Codex startup, MCP, and transport failures."""
    text = detail.lower()
    markers = (
        "mcp startup failed",
        "failed to initialize mcp",
        "handshaking with mcp",
        "error sending request",
        "http/request failed",
        "connection refused",
        "connection reset",
        "network is unreachable",
        "temporary failure in name resolution",
        "dns lookup failed",
    )
    return any(marker in text for marker in markers)


# Keywords Codex's strict response_format rejects outright (HTTP 400
# invalid_json_schema). They are dropped from the wire copy only: the caller's
# schema is never mutated, so local jsonschema validation still enforces them
# after the response arrives.
_CODEX_UNSUPPORTED_KEYWORDS = frozenset(
    {"$schema", "$id", "title", "uniqueItems", "allOf", "if", "then", "else", "not"}
)


def _codex_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize JSON Schema to the strict object subset accepted by Codex."""
    normalized: dict[str, Any] = {}
    for key, value in schema.items():
        if key in _CODEX_UNSUPPORTED_KEYWORDS:
            continue
        if key == "additionalProperties":
            continue
        if key == "properties" and isinstance(value, dict):
            # `properties` maps field names to schemas: its keys are data, not
            # annotations. A field literally called "title" must survive, and it
            # used to be stripped alongside the `title` keyword of the same name,
            # which removed it from the wire schema and left local validation
            # waiting for a field Codex was never asked to produce.
            normalized[key] = {
                name: _codex_strict_schema(sub) if isinstance(sub, dict) else sub
                for name, sub in value.items()
            }
            continue
        if isinstance(value, dict):
            normalized[key] = _codex_strict_schema(value)
        elif isinstance(value, list):
            normalized[key] = [
                _codex_strict_schema(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            normalized[key] = value

    # Free-form maps (object + additionalProperties: <schema>) are rejected by Codex
    # strict mode. Rewrite them as [{key,value}] arrays before sealing the object.
    additional = schema.get("additionalProperties")
    if (
        (schema.get("type") == "object" or "properties" in schema)
        and isinstance(additional, dict)
        and not schema.get("properties")
    ):
        value_schema = _codex_strict_schema(additional)
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "minLength": 1},
                    "value": value_schema,
                },
                "required": ["key", "value"],
                "additionalProperties": False,
            },
        }

    if normalized.get("type") == "object" or "properties" in normalized:
        properties = normalized.setdefault("properties", {})
        # Codex rejects object schemas that omit properties entirely.
        if not isinstance(properties, dict):
            properties = {}
            normalized["properties"] = properties
        normalized["additionalProperties"] = False
        normalized["required"] = list(properties.keys())
    return normalized


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model: str = model or os.getenv("HACKFORGE_OPENAI_MODEL") or "gpt-4o"
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

    @_RETRY
    def complete(self, system: str, user: str, *, temperature: float = 0.4) -> LLMResponse:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, timeout=float(os.getenv("HACKFORGE_LLM_TIMEOUT", "90")))
        resp = client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            raw={"id": getattr(resp, "id", None)},
        )


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model: str = model or os.getenv("HACKFORGE_ANTHROPIC_MODEL") or "claude-sonnet-4-20250514"
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

    @_RETRY
    def complete(self, system: str, user: str, *, temperature: float = 0.4) -> LLMResponse:
        import anthropic

        client = anthropic.Anthropic(
            api_key=self.api_key,
            timeout=float(os.getenv("HACKFORGE_LLM_TIMEOUT", "90")),
        )
        resp = client.messages.create(
            model=self.model,
            max_tokens=8192,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in resp.content if hasattr(block, "text"))
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            prompt_tokens=getattr(usage, "input_tokens", None),
            completion_tokens=getattr(usage, "output_tokens", None),
            raw={"id": getattr(resp, "id", None)},
        )


@dataclass
class ProviderBundle:
    research: LLMProvider
    ideation_lanes: list[LLMProvider]
    collision: LLMProvider
    feasibility: LLMProvider
    judges: LLMProvider
    red_team: LLMProvider
    dry_run: bool = False


def load_providers(
    *,
    dry_run: bool = False,
    fixture_bundle: dict[str, Any] | None = None,
    provider: str = "deepseek",
) -> ProviderBundle:
    load_dotenv()
    dry = dry_run or provider == "dry-run"

    if dry:
        dry_p = DryRunProvider(fixture_bundle)
        return ProviderBundle(
            research=dry_p,
            ideation_lanes=[dry_p, dry_p, dry_p, dry_p],
            collision=dry_p,
            feasibility=dry_p,
            judges=dry_p,
            red_team=dry_p,
            dry_run=True,
        )

    providers: list[LLMProvider] = []
    if provider in {"deepseek", "auto"}:
        # `auto` is retained as a backwards-compatible alias, but intentionally
        # resolves to DeepSeek only. It never probes or falls back to Codex.
        from hackforge.providers.deepseek_provider import DeepSeekProvider

        providers = [DeepSeekProvider()]
    elif provider == "codex":
        providers = [CodexExecProvider()]
    elif provider == "litellm" and env_flag("HACKFORGE_USE_LITELLM", default=True):
        from hackforge.providers.litellm_provider import LiteLLMProvider, litellm_models_from_env

        models = litellm_models_from_env()
        if not models:
            raise RuntimeError("LiteLLM was selected but no supported provider API key is configured")
        for model in models:
            providers.append(LiteLLMProvider(model))
    if not providers:
        raise RuntimeError(
            f"Requested provider {provider!r} is unavailable or disabled. No provider fallback was attempted."
        )

    # Alternate providers across ideation lanes for isolation when both exist
    lanes = [providers[i % len(providers)] for i in range(4)]
    primary = providers[0]
    secondary = providers[1] if len(providers) > 1 else providers[0]
    return ProviderBundle(
        research=primary,
        ideation_lanes=lanes,
        collision=secondary,
        feasibility=secondary,
        judges=primary,
        red_team=secondary,
        dry_run=False,
    )
