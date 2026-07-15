from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ClaimConfidence = Literal["high", "medium", "low"]
CollisionRisk = Literal["low", "medium", "high", "unknown"]
DeliveryRisk = Literal["low", "medium", "high"]


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
    team_size: str | None = None
    required_or_encouraged_tech: list[str] = Field(default_factory=list)
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
