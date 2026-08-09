from __future__ import annotations

from hackforge.evaluation.gates import evaluate_gates, passes_gates
from hackforge.models import (
    CandidateIdea,
    CompetitionBrief,
    CompetitionRequirement,
    EvidenceSource,
    JudgingCriterion,
)
from hackforge.paths import EVALS_DIR


def _evidence() -> EvidenceSource:
    return EvidenceSource(
        id="brief",
        url="input://competition-brief",
        title="Competition brief",
        source_kind="input",
        retrieved_at="2026-08-09T00:00:00+00:00",
        verified=True,
    )


def _idea(identifier: str) -> CandidateIdea:
    return CandidateIdea(
        id=identifier,
        primary_user="competition stakeholder",
        painful_workflow="complete the competition objective under the stated constraints",
        current_workaround="manual or existing process",
        imported_mechanism="constraint-driven design",
        core_computation="apply the required mechanism and validate the resulting artifact",
        last_mile_action="produce the judged result",
        visible_transformation="initial state becomes a validated competition result",
        killer_demo="present or inspect the required proof when the competition calls for it",
        evidence_ids=["brief"],
    )


def test_hardware_competition_does_not_require_software_or_public_data():
    brief = CompetitionBrief(
        name="Autonomous Field Robotics Challenge",
        build_window="36 hours",
        team_size="2-5",
        submission_artifacts=["physical prototype", "safety checklist"],
        demo_requirements=["live field demonstration"],
        judging_criteria=[
            JudgingCriterion(name="Task completion and reliability", weight_or_priority="40%"),
            JudgingCriterion(name="Safety and robustness", weight_or_priority="25%"),
        ],
    )
    idea = _idea("robot")
    idea.data_sources = []
    idea.data_access_status = "not_required"
    idea.technology_roles = {}
    idea.minimum_demonstrable_loop = (
        "Within 36 hours with the team, prepare hardware, integrate the core mechanism, "
        "test safety and reliability, and validate the physical prototype in the field."
    )
    idea.demo_proof = "Demonstrate the physical prototype completing the marked field task"
    idea.requirement_satisfaction = {
        "artifact:physical prototype": "Build and validate the physical prototype",
        "artifact:safety checklist": "Complete and submit the safety checklist",
    }

    evaluate_gates(idea, brief, [_evidence()])
    assert passes_gates(idea)
    statuses = {result.gate: result.status for result in idea.gate_results}
    assert statuses["required_technology_fit"] == "not_applicable"
    assert statuses["data_viability"] == "not_applicable"


def test_pitch_competition_does_not_invent_code_data_or_demo_gate():
    brief = CompetitionBrief(
        name="Early-Stage Startup Pitch Competition",
        submission_artifacts=["slide deck"],
        judging_criteria=[
            JudgingCriterion(name="Customer problem and evidence", weight_or_priority="30%"),
            JudgingCriterion(name="Market opportunity and business model", weight_or_priority="25%"),
        ],
    )
    idea = _idea("pitch")
    idea.data_sources = []
    idea.data_access_status = "not_required"
    idea.technology_roles = {}
    idea.requirement_satisfaction = {
        "artifact:slide deck": "Prepare the required investor-facing slide deck"
    }

    evaluate_gates(idea, brief, [_evidence()])
    assert passes_gates(idea)
    statuses = {result.gate: result.status for result in idea.gate_results}
    assert statuses["required_technology_fit"] == "not_applicable"
    assert statuses["data_viability"] == "not_applicable"
    assert statuses["demo_fit"] == "not_applicable"


def test_grant_eligibility_is_not_scored_as_an_idea_property():
    brief = CompetitionBrief(
        name="Applied Research Seed Grant",
        requirements=[
            CompetitionRequirement(
                id="eligibility-affiliation",
                category="eligibility",
                description="Applicant must be affiliated with an eligible research institution",
                required=True,
            )
        ],
        submission_artifacts=["research proposal", "budget and justification"],
        judging_criteria=[
            JudgingCriterion(name="Research significance", weight_or_priority="high"),
            JudgingCriterion(name="Methodological quality", weight_or_priority="high"),
        ],
    )
    idea = _idea("grant")
    idea.data_sources = []
    idea.data_access_status = "not_required"
    idea.technology_roles = {}
    idea.requirement_satisfaction = {
        "artifact:research proposal": "Prepare the research proposal",
        "artifact:budget and justification": "Prepare the budget and justification",
    }

    evaluate_gates(idea, brief, [_evidence()])
    assert passes_gates(idea)
    requirement_gate = next(
        result for result in idea.gate_results if result.gate == "requirement_compliance"
    )
    assert requirement_gate.status == "pass"
    assert "eligibility-affiliation" not in requirement_gate.reason


def test_benchmark_suite_covers_six_distinct_formats():
    briefs = list((EVALS_DIR / "benchmark-hackathons").glob("*.md"))
    headings = {path.read_text(encoding="utf-8").splitlines()[0] for path in briefs}
    assert len(briefs) >= 6
    assert len(headings) == len(briefs)
