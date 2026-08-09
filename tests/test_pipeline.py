from __future__ import annotations

from hackforge.evaluation.gates import evaluate_gates, passes_gates
from hackforge.ideation import cluster_ideas, select_diversified
from hackforge.models import CandidateIdea, CompetitionBrief, EvidenceSource
from hackforge.paths import FIXTURES_DIR, REPO_ROOT
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
    assert {selected_item.id for selected_item in selected} != {"a", "b"} or len(clusters) == 1


def test_non_url_data_is_allowed_when_access_is_credible():
    brief = CompetitionBrief(name="Data Challenge", data_requirements=["Use the provided dataset"])
    idea = CandidateIdea(
        id="provided-data",
        primary_user="analyst",
        painful_workflow="modeling a supplied benchmark",
        current_workaround="manual baseline",
        imported_mechanism="robust optimization",
        data_sources=["competition-provided training dataset"],
        core_computation="train and validate a constrained model",
        last_mile_action="submit benchmark result",
        visible_transformation="baseline becomes validated result",
        killer_demo="show measured benchmark result",
        demo_proof="show measured benchmark result",
        evidence_ids=["input"],
        data_access_status="provided",
        data_access_plan="Use the dataset supplied by the competition organizer",
    )
    evidence = EvidenceSource(
        id="input",
        url="input://brief",
        title="Competition brief",
        retrieved_at="2026-08-09T00:00:00+00:00",
        source_kind="input",
        verified=True,
    )
    evaluate_gates(idea, brief, [evidence])
    assert passes_gates(idea)


def test_fixture_bundle_remains_available_for_deterministic_benchmarks():
    bundle = read_json(FIXTURES_DIR / "dry-run-bundle.json")
    assert "competition_research" in bundle
    assert "ideation" in bundle
    assert "red_team" in bundle


def test_repo_layout():
    assert (REPO_ROOT / "prompts" / "competition-research" / "v1.md").exists()
    assert (REPO_ROOT / "schemas" / "competition.json").exists()
    assert (REPO_ROOT / "corpora" / "crowded-archetypes" / "default.json").exists()
