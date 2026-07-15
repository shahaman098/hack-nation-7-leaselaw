from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv

from hackforge.utils import env_flag


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, system: str, user: str, *, temperature: float = 0.4) -> LLMResponse:
        raise NotImplementedError

    def complete_json(self, system: str, user: str, *, temperature: float = 0.3) -> Any:
        resp = self.complete(
            system + "\n\nReturn valid JSON only. No markdown fences.",
            user,
            temperature=temperature,
        )
        return extract_json(resp.text)


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
    """Deterministic fixture responses for offline pipeline runs."""

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
            payload = {"note": "unhandled dry-run route", "key": key}
        text = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
        return LLMResponse(text=text, provider=self.name, model=self.model)

    def _route_key(self, system: str, user: str) -> str:
        blob = (system + "\n" + user).lower()
        if "competition-intelligence" in blob or "do not generate product ideas" in blob:
            return "competition_research"
        if "contrarian product researcher" in blob:
            return "ideation"
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


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("HACKFORGE_OPENAI_MODEL", "gpt-4o")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

    def complete(self, system: str, user: str, *, temperature: float = 0.4) -> LLMResponse:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
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
        self.model = model or os.getenv("HACKFORGE_ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

    def complete(self, system: str, user: str, *, temperature: float = 0.4) -> LLMResponse:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
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


def load_providers(*, dry_run: bool = False, fixture_bundle: dict[str, Any] | None = None) -> ProviderBundle:
    load_dotenv()
    dry = dry_run or env_flag("HACKFORGE_DRY_RUN")

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
    if os.getenv("OPENAI_API_KEY"):
        providers.append(OpenAIProvider())
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append(AnthropicProvider())
    if not providers:
        raise RuntimeError(
            "No LLM providers configured. Set OPENAI_API_KEY and/or ANTHROPIC_API_KEY, or pass --dry-run."
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
