from __future__ import annotations

from pathlib import Path

import pytest

from hackforge.collision.embed_index import EmbedIndex, structural_text
from hackforge.collision.engine import (
    dimensional_similarity,
    risk_from_dims,
    run_collide_on_ideas,
)
from hackforge.models import CandidateIdea, SimilarityDims
from hackforge.paths import FIXTURES_DIR


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


def test_promptfoo_config_writable():
    from hackforge.evals.promptfoo_runner import ensure_promptfoo_config, run_promptfoo

    path = ensure_promptfoo_config()
    assert path.exists()
    result = run_promptfoo(dry_run=True)
    assert result["status"] == "skipped"
    assert "promptfooconfig.yaml" in result["config"]
