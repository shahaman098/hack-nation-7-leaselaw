from __future__ import annotations

from pathlib import Path

import pytest

from hackforge.collision.corpus_loader import load_candidates
from hackforge.models import CandidateIdea
from hackforge.paths import CORPORA_DIR, FIXTURES_DIR
from hackforge.pipeline import _collect_initial_evidence, run_analyse
from hackforge.profiles import load_competition_profile
from hackforge.utils import read_json
from hackforge.winners.corpus import filter_training_cutoff, load_verified_winners
from hackforge.winners.inspiration import build_inspiration_report, dimension_alignment, score_against_winner
from hackforge.winners.models import VerifiedWinner


def _candidate(**overrides: object) -> CandidateIdea:
    base = {
        "id": "idea-test",
        "primary_user": "Hospital pharmacists reconciling discharge meds",
        "painful_workflow": "Manual cross-check of discharge lists against home prescriptions causes omissions",
        "current_workaround": "spreadsheets",
        "imported_mechanism": "On-chain attestations plus deterministic interaction checker",
        "core_computation": "check interactions",
        "last_mile_action": "generate checklist",
        "visible_transformation": "faster reconciliation",
        "killer_demo": "Live patient case flagged in seconds",
        "evidence_ids": ["brief"],
    }
    base.update(overrides)
    return CandidateIdea.model_validate(base)


def _winner() -> VerifiedWinner:
    return VerifiedWinner(
        id="wn-001",
        project_name="MediChain",
        competition="ETHGlobal Paris",
        year=2023,
        placement="1st",
        source_url="https://devpost.com/software/medichain-eth-paris",
        primary_user="Hospital pharmacists reconciling discharge meds",
        problem="Manual cross-check of discharge lists against home prescriptions causes dangerous omissions",
        mechanism="On-chain attestations plus deterministic interaction checker",
        demo_hook="Live patient case: flagged interaction in 4 seconds",
        event_date="2023-06-15",
    )


def test_verified_winner_corpus_has_minimum_seed_rows():
    winners = load_verified_winners()
    assert len(winners) >= 25


def test_training_cutoff_excludes_recent_winners(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HACKFORGE_TRAINING_CUTOFF", "2022-12-31")
    winners = filter_training_cutoff(load_verified_winners())
    assert all(w.event_date <= "2022-12-31" for w in winners)
    assert not any(w.id == "wn-024" for w in winners)


def test_inspiration_threshold_default_030(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("HACKFORGE_INSPIRATION_MIN", raising=False)
    winner = _winner()
    candidate = _candidate()
    match = score_against_winner(candidate, winner, inspiration_min=0.30, clone_dimension_min=0.72)
    assert match.aggregate_score >= 0.30
    assert match.exceeds_threshold


def test_clone_guard_when_all_three_dimensions_high():
    winner = _winner()
    candidate = _candidate()
    match = score_against_winner(candidate, winner, inspiration_min=0.30, clone_dimension_min=0.10)
    assert match.clone_guard


def test_dimension_alignment_is_bounded():
    score = dimension_alignment("alpha beta gamma", "beta gamma delta")
    assert 0.0 < score <= 1.0


def test_load_competition_profile_hack_nation():
    profile = load_competition_profile("hack-nation")
    assert profile.id == "hack-nation"
    assert profile.inspiration_min == pytest.approx(0.30)
    assert profile.winner_corpus == Path("corpora/verified-winners/seed.jsonl")


def test_combined_url_and_text_ingest(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "hackforge.pipeline.crawl_competition",
        lambda url: [
            __import__("hackforge.models", fromlist=["EvidenceSource"]).EvidenceSource(
                id="u1",
                url=url,
                title="Official",
                source_kind="official",
                retrieved_at="2026-01-01T00:00:00+00:00",
                excerpt="Official rules body",
                fetch_status="ok",
                verified=True,
            )
        ],
    )
    raw, sources, evidence = _collect_initial_evidence(
        input_path=None,
        url="https://competition.example/rules",
        text="Operator notes about judging emphasis",
    )
    assert "Official rules body" in raw
    assert "Operator notes" in raw
    assert "https://competition.example/rules" in sources
    assert len(evidence) >= 2


def test_load_candidates_from_run_dir(tmp_path: Path):
    idea = _candidate(id="idea-abc")
    write_path = tmp_path / "raw-concepts.json"
    write_path.write_text(f"[{idea.model_dump_json()}]", encoding="utf-8")
    loaded = load_candidates(tmp_path)
    assert len(loaded) == 1
    assert loaded[0].id == "idea-abc"


def test_dry_run_pipeline_writes_winner_and_inspiration_artifacts(tmp_path: Path):
    run_dir = run_analyse(
        input_path=FIXTURES_DIR / "sample-hackathon.md",
        dry_run=True,
        fixture_bundle=read_json(FIXTURES_DIR / "dry-run-bundle.json"),
        runs_root=tmp_path,
        search_profile="fast",
        finalists=3,
        visual_report=False,
        competition_profile="hack-nation",
    )
    assert (run_dir / "winner-patterns.json").exists()
    assert (run_dir / "inspiration-report.json").exists()
    patterns = read_json(run_dir / "winner-patterns.json")
    assert patterns.get("mechanism_families")
    report = read_json(run_dir / "inspiration-report.json")
    assert report["inspiration_min"] == pytest.approx(0.30)
    assert report["candidates"]


def test_build_inspiration_report_flags_low_similarity_candidates():
    winners = load_verified_winners()[:5]
    alien = _candidate(
        id="alien",
        primary_user="Mars rover operators",
        painful_workflow="Dust storms obscure solar panel telemetry scheduling",
        imported_mechanism="Orbital relay scheduling with dust opacity forecasts",
    )
    report = build_inspiration_report([alien], winners, inspiration_min=0.30)
    row = report.candidates[0]
    assert row.max_aggregate < 0.30
    assert not row.flagged
