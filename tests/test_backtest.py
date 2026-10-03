from pathlib import Path

import pytest
from click.testing import CliRunner

from hackforge.cli import main
from hackforge.collision.engine import audit_collisions_engine
from hackforge.evals.backtest import run_backtest, score_order, shuffled_control, total_order
from hackforge.paths import REPO_ROOT
from hackforge.utils import read_json, write_json


def test_metric_math_and_shuffle():
    winners = [{"title": "one"}, {"title": "two"}]
    scores = [[1.0, 0.0]] + [[0.0, 0.0]] * 3 + [[0.0, 1.0]]
    metric = score_order(scores, winners)
    assert metric["recall_at_3"] == 0.5
    assert metric["recall_at_12"] == 1.0
    assert metric["mrr"] == 0.6
    assert shuffled_control(scores, winners) == shuffled_control(scores, winners)


def test_total_order_tiers_and_kills(tmp_path: Path):
    raw = [{"id": value} for value in ("final", "judged", "audited", "gated", "killed", "failed")]
    write_json(tmp_path / "raw-concepts.json", raw)
    write_json(tmp_path / "run-manifest.json", {"final_output_ids": ["final"]})
    write_json(tmp_path / "competition-brief.json", {"name": "Test"})
    write_json(tmp_path / "blind-judge-results.json", {
        "candidates": [{"blind_id": "A", "internal_id": "final"}, {"blind_id": "B", "internal_id": "judged"}],
    })
    write_json(tmp_path / "gate-results.json", [
        {"candidate_id": row["id"], "passed": row["id"] != "failed", "external_evaluation_scores": {"score": 1.0}}
        for row in raw
    ])
    write_json(tmp_path / "collision-reports.json", [
        {"candidate_id": "audited", "collision_risk": "low", "kill_recommendation": False},
        {"candidate_id": "killed", "collision_risk": "high", "kill_recommendation": True},
    ])
    write_json(tmp_path / "feasibility-reports.json", [])
    assert [row["id"] for row in total_order(tmp_path)] == ["final", "judged", "audited", "gated", "failed", "killed"]


def test_live_guards_and_unverified_data(tmp_path: Path):
    cases = REPO_ROOT / "evals/backtest/cases.json"
    with pytest.raises(ValueError, match="--live"):
        run_backtest(cases, provider="codex")
    with pytest.raises(ValueError, match="verified winner"):
        run_backtest(cases, results_dir=tmp_path)


def test_fixture_batch(tmp_path: Path):
    result = run_backtest(REPO_ROOT / "evals/backtest/fixtures/cases.json", results_dir=tmp_path)
    report = read_json(result)
    assert len(report["cases"]) == 2
    assert report["verdict"] == "insufficient_data"
    for row in report["cases"]:
        assert set(row["controls"]) == {"shuffled", "naive_fixture", "naive_live"}
        run_dir = Path(row["run_dir"])
        ordered = total_order(run_dir)
        assert len(ordered) == len({idea["id"] for idea in ordered}) == row["pool_size"]
        assert read_json(run_dir / "run-manifest.json")["source"] == "backtest"
        assert row["leakage"]["live_research"] is False
    assert result.with_suffix(".md").exists()


def test_cli_backtest_help():
    assert CliRunner().invoke(main, ["eval", "backtest", "--help"]).exit_code == 0


def test_winner_exclusion_before_collision_prompt(monkeypatch):
    from hackforge.models import CandidateIdea
    from hackforge.providers import LLMProvider

    winner = {"name": "Planted Winner", "url": "https://example.org/winner", "similarity": 0.8}
    safe = {"name": "Independent analogue", "url": "https://example.org/safe", "similarity": 0.2}
    monkeypatch.setattr("hackforge.collision.engine.retrieve_analogues", lambda *args, **kwargs: [winner, safe])
    candidate = CandidateIdea(
        id="test", primary_user="Independent analogue users", painful_workflow="workflow",
        current_workaround="manual", imported_mechanism="mechanism", core_computation="computation",
        last_mile_action="action", visible_transformation="transformation", killer_demo="demo",
        collision_risk="low",
    )

    class CaptureProvider(LLMProvider):
        def complete(self, system, user, **kwargs):
            raise AssertionError("complete_json expected")

        def complete_json(self, system, user, **kwargs):
            assert "Planted Winner" not in user
            assert "https://example.org/winner" not in user
            assert "Independent analogue" in user
            return {"reports": [{"candidate_id": "test", "collision_risk": "low", "nearest_analogues": [],
                                 "observable_differentiator": "demo", "differentiator_is_substantive": True,
                                 "kill_recommendation": False, "notes": "checked"}]}

    reports = audit_collisions_engine(CaptureProvider(), [candidate], live_enrich=False,
                                      supplemental_analogues=[winner], exclude=["planted winner"])
    assert reports[0].candidate_id == "test"
    heuristic = audit_collisions_engine(None, [candidate], use_llm=False, live_enrich=False,
                                        exclude=["https://example.org/winner"])
    assert [analogue.name for analogue in heuristic[0].nearest_analogues] == ["Independent analogue"]


def test_bare_eval_preserved(monkeypatch, tmp_path: Path):
    calls = []
    monkeypatch.setattr("hackforge.cli.run_benchmark", lambda *args, **kwargs: calls.append("benchmark") or tmp_path)
    assert CliRunner().invoke(main, ["eval", "--no-promptfoo"]).exit_code == 0
    assert calls == ["benchmark"]
    calls.clear()
    assert CliRunner().invoke(main, ["eval", "backtest", "--help"]).exit_code == 0
    assert not calls


def test_live_naive_shares_run_budget_provider(monkeypatch, tmp_path: Path):
    from hackforge.paths import FIXTURES_DIR
    from hackforge.providers import load_providers

    bundle = load_providers(dry_run=True, fixture_bundle=read_json(FIXTURES_DIR / "dry-run-bundle.json"))
    selections = []

    def select(**kwargs):
        selections.append(kwargs)
        return bundle

    monkeypatch.setattr("hackforge.evals.backtest.load_providers", select)
    # Exercise the live orchestration offline, using a fake verified case and fixture backend.
    cases = read_json(REPO_ROOT / "evals/backtest/fixtures/cases.json")[:1]
    cases[0]["synthetic"] = False
    cases[0]["cutoff_class"] = "unknown"
    case_path = tmp_path / "cases.json"
    write_json(case_path, cases)
    output = run_backtest(case_path, provider="codex", live=True, max_cases=1, results_dir=tmp_path)
    assert len(selections) == 1  # no fresh provider/budget for the live-naive control
    assert read_json(output)["cases"][0]["naive_ideas"]["live"]
    assert read_json(output)["verdict"] == "insufficient_data"
