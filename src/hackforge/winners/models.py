from __future__ import annotations

from pydantic import BaseModel, Field


class VerifiedWinner(BaseModel):
    id: str
    project_name: str
    competition: str
    year: int
    placement: str
    track: str = ""
    source_url: str
    primary_user: str
    problem: str
    mechanism: str
    demo_hook: str
    event_date: str
    tags: list[str] = Field(default_factory=list)


class InspirationDimensions(BaseModel):
    user_alignment: float = 0.0
    problem_alignment: float = 0.0
    mechanism_alignment: float = 0.0


class InspirationMatch(BaseModel):
    winner_id: str
    project_name: str
    source_url: str
    dimensions: InspirationDimensions
    aggregate_score: float
    exceeds_threshold: bool = False
    clone_guard: bool = False


class CandidateInspirationScore(BaseModel):
    candidate_id: str
    nearest_matches: list[InspirationMatch] = Field(default_factory=list)
    max_aggregate: float = 0.0
    clone_guard: bool = False
    flagged: bool = False


class InspirationReport(BaseModel):
    inspiration_min: float
    training_cutoff: str | None = None
    clone_dimension_min: float
    corpus_size: int
    candidates: list[CandidateInspirationScore] = Field(default_factory=list)


class TrackHint(BaseModel):
    track: str
    mechanisms: list[str] = Field(default_factory=list)


class WinnerPatterns(BaseModel):
    competition: str
    winning_archetypes: list[str] = Field(default_factory=list)
    mechanism_families: list[str] = Field(default_factory=list)
    demo_patterns: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)
    track_hints: list[TrackHint] = Field(default_factory=list)
    source_winner_ids: list[str] = Field(default_factory=list)
