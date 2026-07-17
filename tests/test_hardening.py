from __future__ import annotations

import json
import runpy
from pathlib import Path
from stat import S_IMODE
from types import SimpleNamespace

import httpx
import pytest
from click.testing import CliRunner

import hackforge.diagnostics as diagnostics
import hackforge.research as research
from hackforge.cli import main
from hackforge.diagnostics import doctor_ready_for_live, run_doctor
from hackforge.memory import build_run_manifest, learn_from_runs, list_runs
from hackforge.models import EvidenceSource
from hackforge.paths import FIXTURES_DIR
from hackforge.pipeline import run_analyse
from hackforge.providers import (
    LLMProvider,
    LLMResponse,
    ProviderConfigurationError,
    extract_json,
    load_providers,
)
from hackforge.providers.deepseek_provider import DeepSeekProvider
from hackforge.providers.litellm_provider import LiteLLMProvider, litellm_models_from_env
from hackforge.utils import read_json, write_json


class _FlakyJSONProvider(LLMProvider):
    """Returns junk first, then valid JSON — exercises complete_json retries."""

    name = "flaky"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, system: str, user: str, *, temperature: float = 0.4) -> LLMResponse:
        self.calls += 1
        text = "not json at all" if self.calls == 1 else '{"ok": true}'
        return LLMResponse(text=text, provider=self.name, model="test")


def test_extract_json_variants():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('prefix {"a": 2} suffix') == {"a": 2}
    assert extract_json("[1, 2, 3]") == [1, 2, 3]


def test_complete_json_retries_until_valid():
    p = _FlakyJSONProvider()
    result = p.complete_json("sys", "user")
    assert result == {"ok": True}
    assert p.calls == 2


def test_complete_json_raises_after_exhausting_retries():
    class _AlwaysJunk(LLMProvider):
        name = "junk"

        def complete(self, system, user, *, temperature=0.4):
            return LLMResponse(text="never json", provider=self.name, model="test")

    with pytest.raises(ValueError):
        _AlwaysJunk().complete_json("s", "u", retries=1)


def test_complete_json_supplies_exact_schema_and_validation_error_on_retry():
    class _SchemaAware(LLMProvider):
        name = "schema-aware"

        def __init__(self) -> None:
            self.systems: list[str] = []

        def complete(self, system, user, *, temperature=0.4):
            del user, temperature
            self.systems.append(system)
            payload = '{"wrong":true}' if len(self.systems) == 1 else '{"answer":7}'
            return LLMResponse(text=payload, provider=self.name, model="test")

    provider = _SchemaAware()
    schema = {
        "type": "object",
        "required": ["answer"],
        "additionalProperties": False,
        "properties": {"answer": {"type": "integer"}},
    }
    assert provider.complete_json("system", "user", schema=schema) == {"answer": 7}
    assert "exact JSON Schema" in provider.systems[0]
    assert '"required":["answer"]' in provider.systems[0]
    assert "failed parsing or schema validation" in provider.systems[1]
    assert "'answer' is a required property" in provider.systems[1]


def test_doctor_runs_and_reports():
    checks = run_doctor()
    names = {c.name for c in checks}
    assert {"python", "prompts", "codex", "llm_access"} <= names
    # Boolean regardless of local config
    assert isinstance(doctor_ready_for_live(checks), bool)


def test_doctor_can_preflight_codex_without_a_deepseek_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("HACKFORGE_REQUIRE_SEMANTIC_COLLISION", "0")
    monkeypatch.setattr(
        diagnostics.shutil,
        "which",
        lambda binary: "/fake/codex" if binary == "codex" else None,
    )
    monkeypatch.setattr(
        diagnostics.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="Logged in", stderr=""),
    )

    checks = {check.name: check for check in run_doctor(provider="codex")}
    assert checks["codex"].ok and checks["codex"].level == "error"
    assert not checks["deepseek"].ok and checks["deepseek"].level == "warn"
    assert checks["llm_access"].ok
    assert doctor_ready_for_live(list(checks.values()))


def test_live_doctor_probes_the_selected_codex_provider(monkeypatch: pytest.MonkeyPatch):
    from hackforge.providers import CodexExecProvider

    monkeypatch.setenv("HACKFORGE_REQUIRE_SEMANTIC_COLLISION", "0")
    monkeypatch.setattr(
        diagnostics.shutil,
        "which",
        lambda binary: "/fake/codex" if binary == "codex" else None,
    )
    monkeypatch.setattr(
        diagnostics.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="Logged in", stderr=""),
    )
    monkeypatch.setattr(CodexExecProvider, "complete_json", lambda *args, **kwargs: {"ok": True})
    source = EvidenceSource(
        id="src-test",
        url="https://example.test/project",
        title="Project",
        source_kind="github",
        retrieved_at="2026-07-17T00:00:00+00:00",
        excerpt="real result",
        verified=True,
    )
    monkeypatch.setattr(research, "search_github_projects", lambda *args, **kwargs: [source])
    monkeypatch.setattr(
        research,
        "search_devpost_projects",
        lambda *args, **kwargs: [source.model_copy(update={"source_kind": "devpost"})],
    )

    checks = {check.name: check for check in run_doctor(live_probe=True, provider="codex")}
    assert checks["codex_live"].ok
    assert "deepseek_live" not in checks


def test_explicit_hackforge_home_relocates_checkout_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    state_root = tmp_path / "private-state"
    monkeypatch.setenv("HACKFORGE_HOME", str(state_root))
    paths = runpy.run_path(str(FIXTURES_DIR.parent / "src" / "hackforge" / "paths.py"))

    assert paths["RUNS_DIR"] == state_root / "runs"
    assert paths["CORPUS_CACHE_DIR"] == state_root / "corpora" / "cache"
    assert paths["INDEX_DIR"] == state_root / "corpora" / "indexes" / "default"
    assert paths["HACKREP_DIR"] == state_root / "corpora" / "hackrep"


def test_deepseek_is_a_first_class_litellm_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("HACKFORGE_DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert litellm_models_from_env() == ["deepseek/deepseek-v4-pro"]
    provider = LiteLLMProvider("deepseek/deepseek-v4-pro")
    assert provider.name == "litellm-deepseek"


def test_deepseek_direct_provider_uses_adaptive_thinking_without_temperature():
    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "response-1",
                "choices": [{"message": {"content": '{"winner": "idea-1"}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(api_key="test-key", model="deepseek-v4-pro", client=client)
        result = provider.complete(
            "You are a blind hackathon judge with role: pairwise-comparator.",
            "Choose one",
            temperature=0.9,
        )

    assert result.model == "deepseek-v4-pro"
    assert result.raw == {
        "id": "response-1",
        "thinking": "enabled",
        "reasoning_effort": "max",
    }
    assert requests[0]["thinking"] == {"type": "enabled"}
    assert requests[0]["reasoning_effort"] == "max"
    assert requests[0]["max_tokens"] == 4096
    assert "temperature" not in requests[0]


def test_deepseek_adaptive_profile_uses_high_for_extraction(monkeypatch: pytest.MonkeyPatch):
    provider = DeepSeekProvider(api_key="test-key", model="deepseek-v4-pro")
    assert provider._reasoning_effort("You are the competition-intelligence researcher.") == "high"
    assert provider._reasoning_effort("You are a concept-crossing-engine.") == "high"
    assert provider._reasoning_effort("You are a blind hackathon judge.") == "max"
    assert not provider._thinking_enabled("You are an opportunity-card-generator.")
    assert not provider._thinking_enabled("You are the collision auditor.")
    assert not provider._thinking_enabled("You are the feasibility reviewer.")
    assert not provider._thinking_enabled("You are a blind hackathon judge with role: technical.")
    assert provider._thinking_enabled("You are a blind hackathon judge with role: pairwise-comparator.")
    monkeypatch.setenv("HACKFORGE_DEEPSEEK_REVIEW_THINKING", "1")
    assert provider._thinking_enabled("You are the collision auditor.")
    monkeypatch.setenv("HACKFORGE_DEEPSEEK_JUDGE_VOTE_THINKING", "1")
    assert provider._thinking_enabled("You are a blind hackathon judge with role: technical.")
    assert provider._max_tokens_for("You are the collision auditor.") == 4096


def test_deepseek_streaming_completion_collects_final_content_and_usage():
    events = "\n\n".join(
        [
            'data: {"id":"stream-1","choices":[{"delta":{"reasoning_content":"think"},"finish_reason":null}]}',
            'data: {"id":"stream-1","choices":[{"delta":{"content":"{\\"ok\\":"},"finish_reason":null}]}',
            'data: {"id":"stream-1","choices":[{"delta":{"content":"true}"},"finish_reason":"stop"}],"usage":{"prompt_tokens":7,"completion_tokens":5}}',
            "data: [DONE]",
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["stream"] is True
        assert payload["stream_options"] == {"include_usage": True}
        return httpx.Response(
            200,
            content=events,
            headers={"content-type": "text/event-stream"},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(api_key="test-key", model="deepseek-v4-pro", client=client)
        result = provider.complete("system", "user")

    assert result.text == '{"ok":true}'
    assert provider.usage_snapshot()["total_tokens"] == 12


def test_deepseek_stream_enforces_total_deadline():
    from hackforge.providers.deepseek_provider import _DeepSeekTransientError

    response = httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        content=b'data: {"choices": []}\n\ndata: [DONE]\n\n',
    )
    provider = DeepSeekProvider(api_key="test-key", model="deepseek-v4-pro")
    with pytest.raises(_DeepSeekTransientError, match="total deadline"):
        provider._consume_stream(response, deadline=0)


def test_deepseek_permanent_error_fails_once_without_fallback():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"error": {"message": "invalid api key"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(api_key="bad-key", model="deepseek-v4-pro", client=client)
        with pytest.raises(ProviderConfigurationError, match="No provider or model fallback"):
            provider.complete("system", "user")
    assert calls == 1


def test_deepseek_enforces_call_budget(monkeypatch: pytest.MonkeyPatch):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "id": "budget-1",
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 1},
            },
        )

    monkeypatch.setenv("HACKFORGE_MAX_LLM_CALLS", "1")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(api_key="test-key", model="deepseek-v4-pro", client=client)
        provider.complete("system", "user")
        with pytest.raises(RuntimeError, match="call budget exhausted"):
            provider.complete("system", "user")
    assert calls == 1
    assert provider.usage_snapshot()["total_tokens"] == 5


def test_deepseek_retries_and_accounts_for_empty_final_answer():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        content = "" if calls == 1 else '{"ok":true}'
        return httpx.Response(
            200,
            json={
                "id": f"retry-{calls}",
                "choices": [
                    {
                        "message": {"content": content, "reasoning_content": "reasoning"},
                        "finish_reason": "length" if not content else "stop",
                    }
                ],
                "usage": {"prompt_tokens": 4, "completion_tokens": 3},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(api_key="test-key", model="deepseek-v4-pro", client=client)
        result = provider.complete("system", "user")

    assert result.text == '{"ok":true}'
    assert calls == 2
    usage = provider.usage_snapshot()
    assert usage["attempted_calls"] == 2
    assert usage["completed_calls"] == 2
    assert usage["total_tokens"] == 14


def test_live_doctor_probes_real_services_without_exposing_secrets(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(
        DeepSeekProvider,
        "probe",
        lambda self: {"ok": True, "model": self.model, "response_id": "probe"},
    )
    source = EvidenceSource(
        id="src-test",
        url="https://example.test/project",
        title="Project",
        source_kind="github",
        retrieved_at="2026-07-17T00:00:00+00:00",
        excerpt="real result",
        verified=True,
    )
    monkeypatch.setattr(research, "search_github_projects", lambda *args, **kwargs: [source])
    monkeypatch.setattr(
        research,
        "search_devpost_projects",
        lambda *args, **kwargs: [source.model_copy(update={"source_kind": "devpost"})],
    )

    checks = {check.name: check for check in run_doctor(live_probe=True)}
    assert checks["deepseek_live"].ok
    assert checks["github_live"].ok
    assert checks["devpost_live"].ok


def test_live_doctor_treats_waf_blocked_devpost_as_nonblocking_by_default(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("HACKFORGE_REQUIRE_SEMANTIC_COLLISION", "0")
    monkeypatch.delenv("HACKFORGE_REQUIRE_LIVE_DEVPOST", raising=False)
    monkeypatch.setattr(
        DeepSeekProvider,
        "probe",
        lambda self: {"ok": True, "model": self.model, "response_id": "probe"},
    )
    source = EvidenceSource(
        id="src-test",
        url="https://example.test/project",
        title="Project",
        source_kind="github",
        retrieved_at="2026-07-17T00:00:00+00:00",
        excerpt="real result",
        verified=True,
    )
    failed_devpost = source.model_copy(
        update={
            "source_kind": "devpost",
            "fetch_status": "failed",
            "verified": False,
            "error": "AWS WAF challenge",
        }
    )
    monkeypatch.setattr(research, "search_github_projects", lambda *args, **kwargs: [source])
    monkeypatch.setattr(
        research,
        "search_devpost_projects",
        lambda *args, **kwargs: [failed_devpost],
    )

    checks = {check.name: check for check in run_doctor(live_probe=True)}
    assert not checks["devpost_live"].ok
    assert checks["devpost_live"].level == "warn"
    assert doctor_ready_for_live(list(checks.values()))

    monkeypatch.setenv("HACKFORGE_REQUIRE_LIVE_DEVPOST", "1")
    strict_checks = {check.name: check for check in run_doctor(live_probe=True)}
    assert strict_checks["devpost_live"].level == "error"
    assert not doctor_ready_for_live(list(strict_checks.values()))


def test_default_bundle_is_deepseek_only_even_when_other_keys_exist(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("HACKFORGE_DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")

    bundle = load_providers()
    selected = [
        bundle.research,
        *bundle.ideation_lanes,
        bundle.collision,
        bundle.feasibility,
        bundle.judges,
        bundle.red_team,
    ]
    assert {provider.name for provider in selected} == {"deepseek"}
    assert {provider.model for provider in selected} == {"deepseek-v4-pro"}
    assert len({id(provider) for provider in selected}) == 1


def test_list_and_learn_runs(tmp_path: Path):
    runs_root = tmp_path / "runs"
    for i, result in enumerate([None, "winner"]):
        run_dir = runs_root / f"2026-01-0{i+1}-demo"
        run_dir.mkdir(parents=True)
        build_run_manifest(
            run_dir=run_dir,
            competition_name="Demo",
            dry_run=True,
            providers={"research": "litellm-openai"},
            input_sources=["inline"],
            input_hash="abc",
            stage_timings={"ideation": 1.5},
            candidate_counts={"raw": 20, "finalists": 3},
            rejections=[],
            final_primary_id="idea-1",
            hackathon_result=result,
        )

    rows = list_runs(runs_root=runs_root)
    assert len(rows) == 2

    report = learn_from_runs(runs_root=runs_root)
    assert report["total_runs"] == 2
    assert report["runs_with_outcomes"] == 1
    assert "litellm-openai" in report["provider_stats"]
    assert report["provider_stats"]["litellm-openai"]["survival_rate"] == pytest.approx(0.15)
    assert report["recommendations"]


def test_failed_run_is_journaled_and_listed(tmp_path: Path):
    runs_root = tmp_path / "runs"
    with pytest.raises(RuntimeError):
        run_analyse(
            input_path=FIXTURES_DIR / "sample-hackathon.md",
            provider="unsupported",
            runs_root=runs_root,
            search_profile="fast",
        )
    run_dir = next(runs_root.iterdir())
    status = read_json(run_dir / "run-status.json")
    assert status["status"] == "failed"
    assert status["stage"] == "provider_selection"
    assert "traceback" not in status
    rows = list_runs(runs_root=runs_root)
    assert rows[0]["status"] == "failed"


def test_artifacts_are_atomic_and_private(tmp_path: Path):
    path = tmp_path / "private" / "artifact.json"
    write_json(path, {"complete": True})
    assert read_json(path) == {"complete": True}
    assert S_IMODE(path.stat().st_mode) == 0o600
    assert not list(path.parent.glob(".artifact.json.*"))


def test_cli_doctor_and_runs_list():
    runner = CliRunner()
    assert runner.invoke(main, ["doctor"]).exit_code == 0
    assert runner.invoke(main, ["runs", "list"]).exit_code == 0
    assert runner.invoke(main, ["--version"]).exit_code == 0


def test_cli_analyse_rejects_fixture_provider(tmp_path: Path):
    result = CliRunner().invoke(
        main,
        [
            "analyse",
            str(FIXTURES_DIR / "sample-hackathon.md"),
            "--provider",
            "dry-run",
            "--search-profile",
            "fast",
            "--output-root",
            str(tmp_path),
            "--no-visual-report",
        ],
    )
    assert result.exit_code != 0
    assert "Invalid value for '--provider'" in result.output
    assert not tmp_path.exists() or not any(tmp_path.iterdir())
