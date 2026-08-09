from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

from hackforge import __version__
from hackforge.paths import CORPUS_CACHE_DIR, INDEX_DIR, PROMPT_VERSIONS, PROMPTS_DIR
from hackforge.utils import env_flag


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    hint: Optional[str] = None
    level: str = "error"  # "error" blocks selected/strict functionality; "warn" is optional enrichment


def _module_available(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def run_doctor(*, live_probe: bool = False, provider: str = "deepseek") -> list[Check]:
    """Verify the selected runtime plus any explicitly strict optional capabilities."""
    if provider not in {"deepseek", "codex", "litellm"}:
        raise ValueError(f"Unsupported provider {provider!r}")
    load_dotenv()
    checks: list[Check] = []

    py_ok = sys.version_info >= (3, 9)
    checks.append(
        Check(
            "python",
            py_ok,
            f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            hint=None if py_ok else "HackForge requires Python >= 3.9.",
        )
    )

    if live_probe and provider == "deepseek":
        try:
            from hackforge.providers.deepseek_provider import DeepSeekProvider

            probe = DeepSeekProvider().probe()
            checks.append(Check("deepseek_live", True, f"chat completion succeeded: {probe['model']}"))
        except Exception as exc:
            checks.append(
                Check(
                    "deepseek_live",
                    False,
                    f"live chat probe failed: {exc}",
                    hint="Verify the key, model entitlement, network access, and account balance.",
                )
            )

    if live_probe:
        from hackforge.research import search_devpost_projects, search_github_projects

        require_github = env_flag("HACKFORGE_REQUIRE_GITHUB_RESEARCH", default=False)
        github_sources = search_github_projects(
            "competition innovation challenge",
            max_results=1,
            token=os.getenv("GITHUB_TOKEN"),
        )
        github_ok = any(source.fetch_status == "ok" for source in github_sources)
        github_error = "; ".join(source.error for source in github_sources if source.error)
        checks.append(
            Check(
                "github_live",
                github_ok,
                (
                    "public repository enrichment succeeded"
                    if github_ok
                    else f"repository enrichment unavailable: {github_error or 'no results'}"
                ),
                hint=(
                    None
                    if github_ok
                    else "Optional: set GITHUB_TOKEN, or HACKFORGE_REQUIRE_GITHUB_RESEARCH=1 to make this blocking."
                ),
                level="error" if require_github else "warn",
            )
        )

        devpost_sources = search_devpost_projects("competition innovation challenge", max_results=1)
        devpost_ok = any(source.fetch_status == "ok" for source in devpost_sources)
        devpost_error = "; ".join(source.error for source in devpost_sources if source.error)
        require_live_devpost = env_flag("HACKFORGE_REQUIRE_LIVE_DEVPOST", default=False)
        checks.append(
            Check(
                "devpost_live",
                devpost_ok,
                (
                    "public project enrichment succeeded"
                    if devpost_ok
                    else f"project enrichment unavailable: {devpost_error or 'no results'}"
                ),
                hint=(
                    None
                    if devpost_ok
                    else "Optional: keep this as enrichment, or set HACKFORGE_REQUIRE_LIVE_DEVPOST=1 to make it blocking."
                ),
                level="error" if require_live_devpost else "warn",
            )
        )

    checks.append(Check("hackforge", True, f"version {__version__}"))

    missing_prompts = [
        f"{family}/{version}"
        for family, version in PROMPT_VERSIONS.items()
        if not (PROMPTS_DIR / family / f"{version}.md").exists()
    ]
    checks.append(
        Check(
            "prompts",
            not missing_prompts,
            "all prompt versions present" if not missing_prompts else f"missing: {', '.join(missing_prompts)}",
            hint=None if not missing_prompts else "Restore the prompts/ directory.",
        )
    )

    openai = bool(os.getenv("OPENAI_API_KEY"))
    anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    deepseek = bool(os.getenv("DEEPSEEK_API_KEY"))
    key_detail = ", ".join(
        [
            name
            for name, present in (
                ("DEEPSEEK", deepseek),
                ("OPENAI", openai),
                ("ANTHROPIC", anthropic),
            )
            if present
        ]
    ) or "none set"

    codex_binary = os.getenv("HACKFORGE_CODEX_BINARY") or shutil.which("codex")
    codex_authenticated = False
    codex_detail = "not installed"
    if codex_binary:
        try:
            status = subprocess.run(
                [codex_binary, "login", "status"],
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
            codex_authenticated = status.returncode == 0 and "logged in" in (
                status.stdout + status.stderr
            ).lower()
            codex_detail = (
                "authenticated" if codex_authenticated else "installed, authentication not confirmed"
            )
        except (OSError, subprocess.TimeoutExpired):
            codex_detail = "installed, status check failed"
    checks.append(
        Check(
            "codex",
            codex_authenticated,
            codex_detail,
            hint=None if codex_authenticated else "Run `codex login` before using --provider codex.",
            level="error" if provider == "codex" else "warn",
        )
    )
    if live_probe and provider == "codex":
        if not codex_authenticated:
            checks.append(
                Check(
                    "codex_live",
                    False,
                    "skipped because Codex login is not confirmed",
                    hint="Run `codex login`, then repeat `hackforge doctor --provider codex --strict --live`.",
                )
            )
        else:
            try:
                from hackforge.providers import CodexExecProvider

                result = CodexExecProvider(
                    timeout=float(os.getenv("HACKFORGE_CODEX_DOCTOR_TIMEOUT", "90"))
                ).complete_json(
                    "Return a health object.",
                    "Set ok to true.",
                    schema={
                        "type": "object",
                        "properties": {"ok": {"type": "boolean"}},
                        "required": ["ok"],
                        "additionalProperties": False,
                    },
                )
                checks.append(
                    Check(
                        "codex_live",
                        result.get("ok") is True,
                        "authenticated Codex completion succeeded",
                        hint="Retry after checking Codex connectivity if this remains unavailable.",
                    )
                )
            except Exception as exc:
                checks.append(
                    Check(
                        "codex_live",
                        False,
                        f"live completion probe failed: {exc}",
                        hint="Check `codex login`, network access, and any configured Codex model.",
                    )
                )

    deepseek_model = os.getenv("HACKFORGE_DEEPSEEK_MODEL", "deepseek-v4-pro").removeprefix(
        "deepseek/"
    )
    model_ok = deepseek_model in {"deepseek-v4-pro", "deepseek-v4-flash"}
    deepseek_ready = deepseek and model_ok
    checks.append(
        Check(
            "deepseek",
            deepseek_ready,
            (
                f"configured: {deepseek_model} (direct official API)"
                if deepseek_ready
                else (
                    f"unsupported model: {deepseek_model}"
                    if deepseek
                    else "DEEPSEEK_API_KEY not set"
                )
            ),
            hint=(
                None
                if deepseek_ready
                else "Set DEEPSEEK_API_KEY and use deepseek-v4-pro or deepseek-v4-flash."
            ),
            level="error" if provider == "deepseek" else "warn",
        )
    )

    litellm_on = env_flag("HACKFORGE_USE_LITELLM", default=False)
    litellm_ok = _module_available("litellm")
    litellm_models: list[str] = []
    if litellm_ok:
        from hackforge.providers.litellm_provider import litellm_models_from_env

        litellm_models = litellm_models_from_env()
    litellm_ready = litellm_on and litellm_ok and bool(litellm_models)
    litellm_detail = (
        f"configured with {len(litellm_models)} model(s)"
        if litellm_ready
        else (
            "enabled but not installed"
            if litellm_on and not litellm_ok
            else ("enabled but no supported provider key is configured" if litellm_on else "disabled")
        )
    )
    checks.append(
        Check(
            "litellm",
            litellm_ready if provider == "litellm" else (litellm_ok or not litellm_on),
            litellm_detail,
            hint=(
                None
                if (litellm_ready if provider == "litellm" else (litellm_ok or not litellm_on))
                else "Install LiteLLM, set HACKFORGE_USE_LITELLM=1, and configure a supported provider key."
            ),
            level="error" if provider == "litellm" else "warn",
        )
    )

    if provider == "deepseek":
        selected_ready = deepseek_ready
        selected_detail = f"selected DeepSeek runtime: {'ready' if deepseek_ready else 'not ready'}"
        selected_hint = "Configure DEEPSEEK_API_KEY; no provider or model fallback is attempted."
    elif provider == "codex":
        selected_ready = codex_authenticated
        selected_detail = f"selected Codex runtime: {'ready' if codex_authenticated else 'not ready'}"
        selected_hint = "Run `codex login`; no API key is needed for --provider codex."
    else:
        selected_ready = litellm_ready
        selected_detail = f"selected LiteLLM runtime: {'ready' if litellm_ready else 'not ready'}"
        selected_hint = "Enable LiteLLM and configure a supported provider key."
    checks.append(
        Check(
            "llm_access",
            selected_ready,
            f"{selected_detail}; provider keys present: {key_detail}",
            hint=None if selected_ready else selected_hint,
        )
    )

    semantic_required = env_flag("HACKFORGE_REQUIRE_SEMANTIC_COLLISION", default=False)
    collision_ok = _module_available("faiss") and _module_available("sentence_transformers")
    checks.append(
        Check(
            "collision_extras",
            collision_ok,
            "faiss + sentence-transformers installed" if collision_ok else "not installed",
            hint=(
                None
                if collision_ok
                else "Optional: pip install 'hackforge[collision]' for semantic collision detection."
            ),
            level="error" if semantic_required else "warn",
        )
    )

    index_ready = (
        (INDEX_DIR / "index.faiss").exists() or any(INDEX_DIR.glob("*.faiss"))
        if INDEX_DIR.exists()
        else False
    )
    cache_ready = CORPUS_CACHE_DIR.exists() and any(CORPUS_CACHE_DIR.glob("*.jsonl"))
    checks.append(
        Check(
            "corpus_index",
            index_ready,
            "FAISS index built"
            if index_ready
            else ("cache present, index not built" if cache_ready else "no corpus"),
            hint=(
                None
                if index_ready
                else "Optional: run `hackforge corpus pull` then `hackforge corpus build-index`, or set HACKFORGE_REQUIRE_SEMANTIC_COLLISION=1 for strict mode."
            ),
            level="error" if semantic_required else "warn",
        )
    )

    if live_probe and semantic_required and collision_ok and index_ready:
        try:
            from hackforge.collision.embed_index import EmbedIndex

            hits = EmbedIndex().search("competition evidence workflow mechanism", k=1)
            if not hits:
                raise RuntimeError("index returned no records")
            checks.append(Check("semantic_live", True, "embedding model and FAISS query succeeded"))
        except Exception as exc:
            checks.append(
                Check(
                    "semantic_live",
                    False,
                    f"semantic query failed: {exc}",
                    hint="Cache the configured embedding model and rebuild the index.",
                )
            )

    node_ok = shutil.which("npx") is not None
    checks.append(
        Check(
            "npx",
            node_ok,
            "available" if node_ok else "not found",
            hint=None if node_ok else "Install Node.js to run `hackforge eval` (Promptfoo).",
            level="warn",
        )
    )

    langfuse_configured = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
    checks.append(
        Check(
            "langfuse",
            langfuse_configured,
            "configured" if langfuse_configured else "not configured",
            hint=None if langfuse_configured else "Optional: set LANGFUSE_* keys for tracing.",
            level="warn",
        )
    )

    return checks


def doctor_ready_for_live(checks: list[Check]) -> bool:
    return all(check.ok for check in checks if check.level == "error")
