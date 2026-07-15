from __future__ import annotations

import os
from typing import Any

from hackforge.providers import LLMProvider, LLMResponse


class LiteLLMProvider(LLMProvider):
    """Unified multi-provider calls via LiteLLM (OpenAI / Anthropic / …)."""

    name = "litellm"

    def __init__(self, model: str, *, api_key: str | None = None):
        self.model = model
        self.api_key = api_key
        # Label lane with underlying family for manifests
        if model.startswith("claude") or "anthropic" in model:
            self.name = "litellm-anthropic"
        elif model.startswith("gpt") or "openai" in model:
            self.name = "litellm-openai"

    def complete(self, system: str, user: str, *, temperature: float = 0.4) -> LLMResponse:
        from litellm import completion

        kwargs: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        resp = completion(**kwargs)
        choice = resp.choices[0]
        text = choice.message.content or ""
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            raw={"id": getattr(resp, "id", None)},
        )


def litellm_models_from_env() -> list[str]:
    models: list[str] = []
    if os.getenv("OPENAI_API_KEY"):
        models.append(os.getenv("HACKFORGE_OPENAI_MODEL", "gpt-4o"))
    if os.getenv("ANTHROPIC_API_KEY"):
        # LiteLLM expects anthropic/ prefix for Anthropic models in many versions
        raw = os.getenv("HACKFORGE_ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        if not raw.startswith("anthropic/") and "claude" in raw:
            models.append(f"anthropic/{raw}")
        else:
            models.append(raw)
    return models
