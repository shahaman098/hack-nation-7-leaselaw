from __future__ import annotations

import json
from pathlib import Path

import pytest

from hackforge.collision.embed_index import EmbedIndex, structural_text
from hackforge.collision.engine import (
    _collision_schema,
    dimensional_similarity,
    risk_from_dims,
    run_collide_on_ideas,
)
from hackforge.models import CandidateIdea, SimilarityDims
from hackforge.paths import FIXTURES_DIR
from hackforge.providers import LLMProvider


def _idea(**kwargs) -> CandidateIdea:
    base = dict(
        id="idea-1",
        primary_user="social-care caseworkers",
        painful_workflow="reconstructing which guidance version applied on decision date for appeals",
        current_workaround="email archaeology",
        imported_mechanism="temporal fault trees and configuration drift detection",
        data_sources=["dated guidance pages"],
        core_computation="diff rule versions",
        last_mile_action="generate dated appeal checklist",
        visible_transformation="hours to minutes",
        killer_demo="paste decision date → guidance diff → checklist",
        hard_to_fake_advantage="auditable version-diff trail",
        working_title="Appeal Path Diff",
        collision_risk="low",
    )
    base.update(kwargs)
    return CandidateIdea(**base)


def test_dimensional_similarity_and_risk():
    idea = _idea()
    analogue = {
        "user": "caseworkers",
        "problem": "benefit appeal deadline guidance versions",
        "mechanism": "fault tree version drift",
        "data": "guidance",
        "action": "checklist",
        "demo": "diff",
    }
    sim = dimensional_similarity(idea, analogue)
    assert isinstance(sim, SimilarityDims)
    assert sim.same_problem or sim.same_mechanism
    risk = risk_from_dims(sim, 0.8)
    assert risk in {"low", "medium", "high"}


def test_collide_offline_no_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HACKFORGE_INDEX_DIR", str(tmp_path / "empty-index"))
    ideas = [_idea(), _idea(id="idea-2", working_title="Other", primary_user="planners")]
    reports, md = run_collide_on_ideas(ideas, live_enrich=False, use_llm=False)
    assert len(reports) == 2
    assert "# Collision analysis" in md
    assert reports[0].candidate_id == "idea-1"


@pytest.mark.slow
def test_build_tiny_faiss_index(tmp_path: Path):
    import json

    records = []
    for line in (FIXTURES_DIR / "tiny-corpus.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    idx = EmbedIndex(tmp_path / "idx")
    try:
        path = idx.build(records)
    except Exception as exc:
        # Allow environments without sentence-transformers / faiss wheels
        pytest.skip(f"collision extras unavailable: {exc}")
    assert path.exists()
    hits = idx.search("caseworkers appeal guidance checklist", k=2)
    assert hits
    assert hits[0]["name"] in {"AppealClock", "StudyBuddy Tutor", "CarbonBoard"}


def test_structural_text():
    idea = _idea()
    text = structural_text(idea)
    assert "caseworkers" in text.lower() or "fault" in text.lower()


def test_collision_schema_bounds_detail_per_candidate():
    report = _collision_schema(2)["properties"]["reports"]["items"]
    analogue = report["properties"]["nearest_analogues"]
    assert analogue["maxItems"] == 3
    assert analogue["items"]["properties"]["differences"]["maxItems"] == 2


def test_audit_payload_drops_fields_the_auditor_never_reads():
    from hackforge.collision.engine import _AUDIT_CANDIDATE_FIELDS, audit_collisions_engine

    class CaptureProvider(LLMProvider):
        def complete(self, system, user, **kwargs):
            raise AssertionError("complete_json expected")

        def complete_json(self, system, user, **kwargs):
            self.user = user
            return {
                "reports": [
                    {
                        "candidate_id": "idea-1",
                        "nearest_analogues": [],
                        "collision_risk": "low",
                        "observable_differentiator": "demo",
                        "differentiator_is_substantive": True,
                        "kill_recommendation": False,
                        "notes": "checked",
                    }
                ]
            }

    idea = _idea(
        requirement_satisfaction={"tech": "a very long per-requirement explanation " * 50},
        technology_roles={"api": "another unused prose block " * 50},
    )
    provider = CaptureProvider()
    audit_collisions_engine(provider, [idea], live_enrich=False)
    payload = json.loads(provider.user)
    sent = payload["candidates"][0]
    # Only audited dimensions cross the wire, and they are valid JSON (no Python repr).
    assert set(sent) == set(_AUDIT_CANDIDATE_FIELDS)
    assert "requirement_satisfaction" not in sent
    assert "technology_roles" not in sent
    assert sent["primary_user"] == "social-care caseworkers"


def test_audit_payload_fails_loud_instead_of_truncating_json(monkeypatch):
    from hackforge.collision import engine

    class CaptureProvider(LLMProvider):
        def complete(self, system, user, **kwargs):
            raise AssertionError("complete_json expected")

        def complete_json(self, system, user, **kwargs):
            raise AssertionError("payload must be rejected before any LLM call")

    # Force the ceiling below the rendered size to prove the guard fires first.
    monkeypatch.setattr(engine, "_MAX_PAYLOAD_CHARS", 10)
    with pytest.raises(RuntimeError, match="refusing to truncate JSON mid-object"):
        engine.audit_collisions_engine(CaptureProvider(), [_idea()], live_enrich=False)


def test_collision_prompt_disables_live_tool_looking():
    from hackforge.utils import load_prompt

    template, _ = load_prompt("collision-audit")
    # Live web search made the audit exceed its timeout; the payload is self-contained.
    assert "Do NOT use web search" in template
    assert "Answer immediately from that payload alone" in template


def test_promptfoo_config_writable():
    from hackforge.evals.promptfoo_runner import ensure_promptfoo_config, run_promptfoo

    path = ensure_promptfoo_config()
    assert path.exists()
    result = run_promptfoo(dry_run=True)
    assert result["status"] == "skipped"
    assert "promptfooconfig.yaml" in result["config"]
