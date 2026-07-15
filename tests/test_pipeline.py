from __future__ import annotations

from pathlib import Path

from hackforge.ideation import cluster_ideas, select_diversified
from hackforge.models import CandidateIdea
from hackforge.paths import FIXTURES_DIR, REPO_ROOT
from hackforge.pipeline import run_analyse
from hackforge.utils import read_json, slugify


def test_slugify():
    assert slugify("Hello World!") == "hello-world"


def test_cluster_and_diversify():
    ideas = [
        CandidateIdea(
            id="a",
            primary_user="caseworker",
            painful_workflow="appeals",
            current_workaround="email",
            imported_mechanism="fault tree",
            data_sources=["x"],
            core_computation="diff",
            last_mile_action="checklist",
            visible_transformation="hours to minutes",
            killer_demo="diff demo",
            hard_to_fake_advantage="audit trail",
            collision_risk="low",
        ),
        CandidateIdea(
            id="b",
            primary_user="caseworker",
            painful_workflow="appeals pack",
            current_workaround="email",
            imported_mechanism="fault tree analysis",
            data_sources=["x"],
            core_computation="diff versions",
            last_mile_action="checklist emit",
            visible_transformation="faster",
            killer_demo="diff demo 2",
            collision_risk="medium",
        ),
        CandidateIdea(
            id="c",
            primary_user="planner",
            painful_workflow="queue",
            current_workaround="spreadsheet",
            imported_mechanism="constraint optimization",
            data_sources=["y"],
            core_computation="solve milp",
            last_mile_action="roster",
            visible_transformation="better queue",
            killer_demo="before after risk",
            hard_to_fake_advantage="numeric delta",
            collision_risk="low",
        ),
    ]
    clusters = cluster_ideas(ideas)
    assert len(clusters) >= 1
    selected = select_diversified(ideas, clusters, limit=2)
    assert len(selected) == 2
    assert {s.id for s in selected} != {"a", "b"} or len(clusters) == 1


def test_dry_run_pipeline(tmp_path: Path):
    bundle = read_json(FIXTURES_DIR / "dry-run-bundle.json")
    run_dir = run_analyse(
        input_path=FIXTURES_DIR / "sample-hackathon.md",
        dry_run=True,
        fixture_bundle=bundle,
        seeds_per_lane=5,
        runs_root=tmp_path / "runs",
    )
    assert (run_dir / "competition-brief.json").exists()
    assert (run_dir / "raw-concepts.json").exists()
    assert (run_dir / "clustered-concepts.json").exists()
    assert (run_dir / "collision-analysis.md").exists()
    assert (run_dir / "feasibility-analysis.md").exists()
    assert (run_dir / "blind-judge-results.json").exists()
    assert (run_dir / "final-recommendation.md").exists()
    assert (run_dir / "run-manifest.json").exists()
    manifest = read_json(run_dir / "run-manifest.json")
    assert manifest["dry_run"] is True
    assert manifest["final_primary_id"]
    assert manifest["prompt_versions"]
    assert manifest["corpora_version"]


def test_repo_layout():
    assert (REPO_ROOT / "prompts" / "competition-research" / "v1.md").exists()
    assert (REPO_ROOT / "schemas" / "competition.json").exists()
    assert (REPO_ROOT / "corpora" / "crowded-archetypes" / "default.json").exists()
