from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ClaimConfidence = Literal["high", "medium", "low"]
CollisionRisk = Literal["low", "medium", "high", "unknown"]
DeliveryRisk = Literal["low", "medium", "high"]
EvidenceKind = Literal["official", "devpost", "github", "corpus", "web", "input"]
EvidenceStatus = Literal["ok", "failed", "rate_limited", "blocked"]
GateStatus = Literal["pass", "fail", "unverified", "not_applicable"]
RequirementCategory = Literal[
    "technology",
    "platform",
    "data",
    "artifact",
    "demo",
    "timebox",
    "team",
    "eligibility",
    "track",
    "sponsor",
    "other",
]


class EvidenceSource(BaseModel):
    id: str
    url: str
    title: str = ""
    source_kind: EvidenceKind = "web"
    retrieved_at: str
    excerpt: str = ""
    fetch_status: EvidenceStatus = "ok"
    http_status: int | None = None
    error: str = ""
    content_hash: str = ""
    verified: bool = False


class OpportunityCard(BaseModel):
    id: str
    user_class: str
    painful_workflow: str
    unmet_need: str
    evidence_ids: list[str] = Field(default_factory=list)
    track: str = ""
    why_now: str = ""
    unresolved_claims: list[str] = Field(default_factory=list)


class MechanismCard(BaseModel):
    id: str
    mechanism_family: str
    mechanism: str
    origin_domain: str
    inputs: list[str] = Field(default_factory=list)
    transformation: str
    outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class IdeaLineage(BaseModel):
    idea_id: str
    parent_ids: list[str] = Field(default_factory=list)
    opportunity_id: str = ""
    mechanism_id: str = ""
    mutation_round: int = 0
    mutation_target: str = "initial_cross"
    mutation_notes: str = ""


class NoveltyVector(BaseModel):
    track: str = ""
    user_class: str = ""
    workflow: str = ""
    mechanism_family: str = ""
    data: str = ""
    last_mile_action: str = ""
    demo_type: str = ""
    embedding_distances: dict[str, float] = Field(default_factory=dict)


class GateResult(BaseModel):
    gate: str
    status: GateStatus
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    validator: str = "deterministic"


class FactClaim(BaseModel):
    claim: str
    source: str
    confidence: ClaimConfidence = "medium"


class InferenceClaim(BaseModel):
    claim: str
    rationale: str


class JudgingCriterion(BaseModel):
    name: str
    weight_or_priority: str
    notes: str = ""


class CompetitionRequirement(BaseModel):
    id: str
    category: RequirementCategory = "other"
    description: str
    required: bool = True
    evidence_ids: list[str] = Field(default_factory=list)


class CrowdingMap(BaseModel):
    high_collision: list[str] = Field(default_factory=list)
    medium_collision: list[str] = Field(default_factory=list)
    potentially_underexplored: list[str] = Field(default_factory=list)
    do_not_build: list[str] = Field(default_factory=list)


class CompetitionBrief(BaseModel):
    name: str
    slug: str = ""
    source_urls: list[str] = Field(default_factory=list)
    theme: str = ""
    tracks: list[str] = Field(default_factory=list)
    sponsors: list[str] = Field(default_factory=list)
    deadline: str | None = None
    build_window: str | None = None
    team_size: str | None = None
    required_tech: list[str] = Field(default_factory=list)
    encouraged_tech: list[str] = Field(default_factory=list)
    # Compatibility input for older saved runs. New research should populate the
    # required/encouraged fields above and the structured requirements below.
    required_or_encouraged_tech: list[str] = Field(default_factory=list)
    requirements: list[CompetitionRequirement] = Field(default_factory=list)
    submission_artifacts: list[str] = Field(default_factory=list)
    demo_requirements: list[str] = Field(default_factory=list)
    data_requirements: list[str] = Field(default_factory=list)
    prizes: list[str] = Field(default_factory=list)
    facts: list[FactClaim] = Field(default_factory=list)
    inference: list[InferenceClaim] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    potentially_stale: list[str] = Field(default_factory=list)
    judging_criteria: list[JudgingCriterion] = Field(default_factory=list)
    sponsor_capabilities: list[str] = Field(default_factory=list)
    available_datasets: list[str] = Field(default_factory=list)
    crowding: CrowdingMap = Field(default_factory=CrowdingMap)
    sanitized_brief: str = ""

    def mandatory_technologies(self) -> list[str]:
        explicit = list(self.required_tech)
        structured = [
            requirement.description
            for requirement in self.requirements
            if requirement.required and requirement.category in {"technology", "platform"}
        ]
        explicit.extend(structured)
        # Only legacy briefs that have none of the new requirement fields use
        # the old combined list. Even then, clearly optional/recommended entries
        # are filtered rather than silently upgraded to mandatory.
        if (
            not explicit
            and not self.required_tech
            and not self.encouraged_tech
            and not self.requirements
            and self.required_or_encouraged_tech
        ):
            optional_markers = ("optional", "encouraged", "recommended", "bonus", "may use", "can use")
            explicit.extend(
                item
                for item in self.required_or_encouraged_tech
                if not any(marker in item.lower() for marker in optional_markers)
            )
        return list(dict.fromkeys(item.strip() for item in explicit if item.strip()))


class CandidateIdea(BaseModel):
    id: str
    lane: str = ""
    disciplines: list[str] = Field(default_factory=list)
    working_title: str = ""
    primary_user: str
    painful_workflow: str
    current_workaround: str
    imported_mechanism: str
    mechanism_origin: str = ""
    data_sources: list[str] = Field(default_factory=list)
    core_computation: str
    last_mile_action: str
    visible_transformation: str
    sponsor_dependency: str = ""
    technical_risk: str = ""
    collision_risk: CollisionRisk = "unknown"
    why_now: str = ""
    kill_reason: str = ""
    killer_demo: str
    hard_to_fake_advantage: str = ""
    cluster_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    opportunity_id: str = ""
    mechanism_id: str = ""
    mutation_history: list[str] = Field(default_factory=list)
    track_fit: str = ""
    technology_roles: dict[str, str] = Field(default_factory=dict)
    requirement_satisfaction: dict[str, str] = Field(default_factory=dict)
    data_access_status: str = "unverified"
    data_access_plan: str = ""
    testable_claim: str = ""
    demo_proof: str = ""
    minimum_demonstrable_loop: str = ""
    mechanism_family: str = ""
    demo_type: str = ""
    external_evaluation_scores: dict[str, float] = Field(default_factory=dict)
    novelty_vector: NoveltyVector | None = None
    gate_results: list[GateResult] = Field(default_factory=list)


class SimilarityDims(BaseModel):
    same_user: bool = False
    same_problem: bool = False
    same_mechanism: bool = False
    same_data: bool = False
    same_action: bool = False
    same_demo: bool = False


class Analogue(BaseModel):
    name: str
    source: str
    url: str = ""
    similarities: SimilarityDims = Field(default_factory=SimilarityDims)
    differences: list[str] = Field(default_factory=list)


class CollisionReport(BaseModel):
    candidate_id: str
    nearest_analogues: list[Analogue] = Field(default_factory=list)
    collision_risk: Literal["low", "medium", "high"] = "medium"
    observable_differentiator: str = ""
    differentiator_is_substantive: bool = False
    kill_recommendation: bool = False
    notes: str = ""


class FeasibilityReport(BaseModel):
    candidate_id: str
    delivery_risk: DeliveryRisk = "medium"
    critical_dependencies: list[str] = Field(default_factory=list)
    fakeable_parts: list[str] = Field(default_factory=list)
    non_fakeable_core: str = ""
    minimum_demonstrable_loop: str = ""
    kill_recommendation: bool = False
    notes: str = ""


class BuildTask(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    owner_role: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    deliverable: str = Field(min_length=1)
    acceptance_test: str = Field(min_length=1)
    time_slot: str | None = None


class BuildPlan(BaseModel):
    candidate_id: str
    scheduling_status: Literal["scheduled", "unscheduled"]
    build_window: str | None = None
    summary: str = Field(min_length=1)
    architecture: list[str] = Field(min_length=1)
    tasks: list[BuildTask] = Field(min_length=1, max_length=8)
    demo_script: list[str] = Field(min_length=1)
    cut_scope: list[str] = Field(default_factory=list)
    submission_checklist: list[str] = Field(default_factory=list)
    feasibility_report: FeasibilityReport

    @model_validator(mode="after")
    def validate_execution_constraints(self) -> BuildPlan:
        if self.feasibility_report.candidate_id != self.candidate_id:
            raise ValueError("Build plan and original feasibility candidate IDs must match")
        if self.scheduling_status == "unscheduled":
            if self.build_window is not None or any(task.time_slot is not None for task in self.tasks):
                raise ValueError("Unscheduled plans cannot invent a build window or task time slots")
        elif not self.build_window or not self.build_window.strip():
            raise ValueError("Scheduled plans require the supplied build window")
        seen: set[str] = set()
        for task in self.tasks:
            if task.id in seen or not set(task.depends_on).issubset(seen):
                raise ValueError("Build tasks must have unique IDs and depend only on earlier tasks")
            seen.add(task.id)
        return self


class JudgeVote(BaseModel):
    role: str
    preferred_blind_id: str
    rationale: str
    scores_by_official_criteria: dict[str, Any] = Field(default_factory=dict)
    hard_gate_failures: list[str] = Field(default_factory=list)
    demo_failure_risk: DeliveryRisk = "medium"


class PairwiseResult(BaseModel):
    pair: list[str]
    winner: str
    reason: str


class EvaluationResult(BaseModel):
    candidates: list[dict[str, str]]
    hard_gates: dict[str, dict[str, Any]] = Field(default_factory=dict)
    judge_votes: list[JudgeVote] = Field(default_factory=list)
    disagreements: list[str] = Field(default_factory=list)
    pairwise: list[PairwiseResult] = Field(default_factory=list)
    recommendation: dict[str, str] = Field(default_factory=dict)
