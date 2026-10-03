from __future__ import annotations

import copy
import json
from pathlib import Path

import httpx
import jsonschema
import pytest
from click.testing import CliRunner

from hackforge.cli import main
from hackforge.models import CandidateIdea, CompetitionBrief, FeasibilityReport
from hackforge.paths import FIXTURES_DIR, SCHEMAS_DIR
from hackforge.pipeline import run_analyse
from hackforge.pipeline.build_plan import build_plan_markdown, create_build_plan
from hackforge.providers import DryRunProvider, load_providers
from hackforge.providers.deepseek_provider import DeepSeekProvider
from hackforge.utils import read_json


def inputs():
    fixture = read_json(FIXTURES_DIR / "dry-run-bundle.json")
    candidate = CandidateIdea.model_validate({**fixture["ideation"][0], "id": "selected"})
    report = FeasibilityReport(
        candidate_id="selected", delivery_risk="high", critical_dependencies=["actual data access"],
        fakeable_parts=["notification shell"], non_fakeable_core="real computation",
        minimum_demonstrable_loop="input to verified output", notes="Original assessment, not regenerated",
    )
    return fixture, candidate, report


@pytest.mark.parametrize("window", [None, "", "not specified", "unknown", "TBD", "No build window stated in brief"])
def test_no_timebox_is_unscheduled_and_reuses_report(window):
    fixture, candidate, report = inputs()
    provider = DryRunProvider(fixture)
    plan = create_build_plan(provider, CompetitionBrief(name="No timebox", build_window=window, deadline="tomorrow"),
                             candidate, report, {"survive_if": "prove the core"})
    assert plan.scheduling_status == "unscheduled"
    assert plan.build_window is None
    assert all(task.time_slot is None for task in plan.tasks)
    assert plan.feasibility_report.model_dump() == report.model_dump()
    assert len(provider.calls) == 1
    jsonschema.validate(plan.model_dump(), read_json(SCHEMAS_DIR / "build-plan.json"))
    assert "no hour/day allocations invented" in build_plan_markdown(plan)


def test_known_timebox_is_preserved():
    fixture, candidate, report = inputs()
    fixture["build_plan"]["tasks"][0]["time_slot"] = "first quarter of the supplied window"
    plan = create_build_plan(DryRunProvider(fixture), CompetitionBrief(name="Sprint", build_window="24 hours"),
                             candidate, report, {})
    assert plan.scheduling_status == "scheduled"
    assert plan.build_window == "24 hours"
    assert plan.tasks[0].time_slot == "first quarter of the supplied window"


def test_no_timebox_rejects_invented_schedule():
    fixture, candidate, report = inputs()
    fixture["build_plan"]["tasks"][0]["time_slot"] = "hour 1"
    provider = DryRunProvider(fixture)
    with pytest.raises(ValueError, match="schema"):
        create_build_plan(provider, CompetitionBrief(name="No timebox"), candidate, report, {})
    assert len(provider.calls) == 1  # no new inference/repair loop


@pytest.mark.parametrize("depends_on", [["missing"], ["inputs"]])
def test_invalid_dependencies_fail_closed(depends_on):
    fixture, candidate, report = inputs()
    fixture["build_plan"]["tasks"][0]["depends_on"] = depends_on
    with pytest.raises(ValueError, match="earlier tasks"):
        create_build_plan(DryRunProvider(fixture), CompetitionBrief(name="Test"), candidate, report, {})


def test_wrong_feasibility_report_fails_before_call():
    fixture, candidate, report = inputs()
    report.candidate_id = "other"
    provider = DryRunProvider(fixture)
    with pytest.raises(ValueError, match="existing feasibility"):
        create_build_plan(provider, CompetitionBrief(name="Test"), candidate, report, {})
    assert not provider.calls


def test_build_plan_shares_existing_deepseek_budget(monkeypatch):
    fixture, candidate, report = inputs()
    monkeypatch.setenv("HACKFORGE_MAX_LLM_CALLS", "1")
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={
            "id": "plan-budget", "choices": [{"message": {"content": json.dumps(fixture["build_plan"])}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        })

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(api_key="test-key", model="deepseek-v4-pro", client=client)
        create_build_plan(provider, CompetitionBrief(name="Test"), candidate, report, {})
        with pytest.raises(RuntimeError, match="call budget exhausted"):
            create_build_plan(provider, CompetitionBrief(name="Test"), candidate, report, {})
        assert provider.usage_snapshot()["completed_calls"] == 1
        assert provider.usage_snapshot()["total_tokens"] == 30
    assert len(requests) == 1


def test_pipeline_plans_post_red_team_primary_and_skip_saves_call(tmp_path: Path):
    fixture, _, _ = inputs()
    fixture["red_team"]["prefer_backup_instead"] = True
    providers = load_providers(dry_run=True, fixture_bundle=copy.deepcopy(fixture))
    root = run_analyse(input_path=FIXTURES_DIR / "sample-hackathon.md", dry_run=True,
                       execution_providers=providers, runs_root=tmp_path, live_research=False)
    manifest = read_json(root / "run-manifest.json")
    plan = read_json(root / "build-plan.json")
    assert plan["candidate_id"] == manifest["final_primary_id"]
    feasibility = next(report for report in read_json(root / "feasibility-reports.json")
                       if report["candidate_id"] == plan["candidate_id"])
    assert plan["feasibility_report"] == feasibility
    assert (root / "build-plan.md").exists()
    assert manifest["optional_stage_call_budget"]["build_plan"] == 1
    assert "build_plan" in manifest["stage_timings_seconds"]
    skip_fixture = copy.deepcopy(fixture)
    skip_fixture["red_team"]["prefer_backup_instead"] = False
    skip_providers = load_providers(dry_run=True, fixture_bundle=skip_fixture)
    skipped = run_analyse(input_path=FIXTURES_DIR / "sample-hackathon.md", dry_run=True,
                          execution_providers=skip_providers, runs_root=tmp_path,
                          live_research=False, build_plan=False)
    skip_manifest = read_json(skipped / "run-manifest.json")
    assert plan["candidate_id"] == skip_manifest["final_output_ids"][1]
    assert plan["candidate_id"] != skip_manifest["final_primary_id"]
    assert skip_manifest["optional_stage_call_budget"]["build_plan"] == 0
    assert not (skipped / "build-plan.json").exists()
    assert not (skipped / "build-plan.md").exists()
    assert len(providers.research.calls) == len(skip_providers.research.calls) + 1


def test_cli_no_build_plan(tmp_path: Path):
    result = CliRunner().invoke(main, ["analyse", "--input", str(FIXTURES_DIR / "sample-hackathon.md"),
                                      "--dry-run", "--no-build-plan", "--no-visual-report",
                                      "--fixture-bundle", str(FIXTURES_DIR / "dry-run-bundle.json"),
                                      "--output-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    root = next(tmp_path.iterdir())
    assert read_json(root / "run-manifest.json")["build_plan"] is False
    assert not (root / "build-plan.json").exists()
