from __future__ import annotations

import copy
from pathlib import Path

import jsonschema
import pytest
from click.testing import CliRunner

from hackforge.cli import main
from hackforge.models import BuildPlan, CompetitionBrief
from hackforge.paths import FIXTURES_DIR, SCHEMAS_DIR
from hackforge.pipeline import run_analyse
from hackforge.pipeline.develop import _safe_product_path, develop_product
from hackforge.providers import DryRunProvider, load_providers
from hackforge.utils import read_json


def _load_bundle() -> dict:
    return read_json(FIXTURES_DIR / "dry-run-bundle.json")


def _unscheduled_plan() -> BuildPlan:
    plan_data = _load_bundle()["build_plan"]
    for task in plan_data["tasks"]:
        task["time_slot"] = None
    return BuildPlan.model_validate(
        {
            **plan_data,
            "candidate_id": "selected",
            "scheduling_status": "unscheduled",
            "build_window": None,
            "feasibility_report": {"candidate_id": "selected"},
        }
    )


def test_pipeline_develop_writes_product_and_report(tmp_path: Path):
    fixture = _load_bundle()
    providers = load_providers(dry_run=True, fixture_bundle=copy.deepcopy(fixture))
    root = run_analyse(
        input_path=FIXTURES_DIR / "sample-hackathon.md",
        dry_run=True,
        execution_providers=providers,
        runs_root=tmp_path,
        live_research=False,
        build_plan=True,
        develop=True,
    )
    manifest = read_json(root / "run-manifest.json")
    assert manifest["develop"] is True
    assert manifest["optional_stage_call_budget"]["develop"] == 1
    assert "develop" in manifest["stage_timings_seconds"]

    report = read_json(root / "development-report.json")
    jsonschema.validate(report, read_json(SCHEMAS_DIR / "development-report.json"))
    assert report["candidate_id"] == read_json(root / "build-plan.json")["candidate_id"]
    assert report["checks_executed"] is False
    assert all(task["check_status"] == "not_run" for task in report["tasks"])
    product = root / "product"
    assert (product / "index.html").exists()
    assert (product / "README.md").exists()
    assert (product / "app.js").exists()

    baseline_providers = load_providers(dry_run=True, fixture_bundle=copy.deepcopy(fixture))
    baseline = run_analyse(
        input_path=FIXTURES_DIR / "sample-hackathon.md",
        dry_run=True,
        execution_providers=baseline_providers,
        runs_root=tmp_path,
        live_research=False,
        build_plan=True,
        develop=False,
    )
    assert not (baseline / "development-report.json").exists()
    extra_calls = len(providers.research.calls) - len(baseline_providers.research.calls)
    assert extra_calls == 1 + len(read_json(root / "build-plan.json")["tasks"])


def test_develop_requires_build_plan(tmp_path: Path):
    fixture = _load_bundle()
    providers = load_providers(dry_run=True, fixture_bundle=copy.deepcopy(fixture))
    with pytest.raises(RuntimeError, match="develop requires build_plan"):
        run_analyse(
            input_path=FIXTURES_DIR / "sample-hackathon.md",
            dry_run=True,
            execution_providers=providers,
            runs_root=tmp_path,
            live_research=False,
            build_plan=False,
            develop=True,
        )


def test_safe_product_path_rejects_escape(tmp_path: Path):
    root = tmp_path / "product"
    root.mkdir()
    assert _safe_product_path(root, "src/app.js") == (root / "src" / "app.js").resolve()
    with pytest.raises(ValueError, match="escapes the product directory"):
        _safe_product_path(root, "../escape.txt")
    with pytest.raises(ValueError, match="escapes the product directory"):
        _safe_product_path(root, "/etc/passwd")


def test_develop_repairs_failed_check_once(tmp_path: Path):
    fixture = _load_bundle()
    fixture["develop_scaffold"]["scaffold"]["run_command"] = None
    fixture["develop_scaffold"]["scaffold"]["url"] = None
    fixture["develop_task"]["check_command"] = 'python3 -c "import sys; sys.exit(1)"'
    provider = DryRunProvider(fixture)
    report = develop_product(
        provider,
        CompetitionBrief(name="Fixture"),
        _unscheduled_plan(),
        tmp_path / "product",
        execute_checks=True,
    )
    assert report.checks_executed is True
    first = report.tasks[0]
    assert first.check_status == "failed"
    assert first.repair_attempts == 1
    assert first.status == "failed"
    assert report.gui_smoke is not None and report.gui_smoke.attempted is False


def test_develop_passing_check(tmp_path: Path):
    fixture = _load_bundle()
    fixture["develop_scaffold"]["scaffold"]["run_command"] = None
    fixture["develop_scaffold"]["scaffold"]["url"] = None
    fixture["develop_task"]["check_command"] = "python3 -c \"print('ok')\""
    provider = DryRunProvider(fixture)
    report = develop_product(
        provider,
        CompetitionBrief(name="Fixture"),
        _unscheduled_plan(),
        tmp_path / "product",
        execute_checks=True,
    )
    assert report.tasks[0].check_status == "passed"
    assert report.tasks[0].status == "implemented"
    assert report.gui_smoke is not None and report.gui_smoke.attempted is False


def test_cli_develop_dry_run(tmp_path: Path):
    result = CliRunner().invoke(
        main,
        [
            "analyse",
            "--input",
            str(FIXTURES_DIR / "sample-hackathon.md"),
            "--dry-run",
            "--no-visual-report",
            "--fixture-bundle",
            str(FIXTURES_DIR / "dry-run-bundle.json"),
            "--output-root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    source = next(tmp_path.iterdir())
    assert (source / "build-plan.json").exists()
    target = tmp_path / "target"
    source.rename(target)
    result = CliRunner().invoke(
        main,
        ["develop", str(target), "--dry-run", "--fixture-bundle", str(FIXTURES_DIR / "dry-run-bundle.json")],
    )
    assert result.exit_code == 0, result.output
    report = read_json(target / "development-report.json")
    assert (target / "product" / report["scaffold"]["entry_point"]).exists()
