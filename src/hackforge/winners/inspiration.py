from __future__ import annotations

import os
import re

from hackforge.models import CandidateIdea

from .models import (
    CandidateInspirationScore,
    InspirationDimensions,
    InspirationMatch,
    InspirationReport,
    VerifiedWinner,
)


def _tokens(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-z0-9]{4,}", (text or "").lower())}


def dimension_alignment(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def score_against_winner(
    candidate: CandidateIdea,
    winner: VerifiedWinner,
    *,
    inspiration_min: float,
    clone_dimension_min: float,
) -> InspirationMatch:
    dims = InspirationDimensions(
        user_alignment=dimension_alignment(candidate.primary_user, winner.primary_user),
        problem_alignment=dimension_alignment(candidate.painful_workflow, winner.problem),
        mechanism_alignment=dimension_alignment(candidate.imported_mechanism, winner.mechanism),
    )
    aggregate = (dims.user_alignment + dims.problem_alignment + dims.mechanism_alignment) / 3.0
    clone_guard = (
        dims.user_alignment >= clone_dimension_min
        and dims.problem_alignment >= clone_dimension_min
        and dims.mechanism_alignment >= clone_dimension_min
    )
    return InspirationMatch(
        winner_id=winner.id,
        project_name=winner.project_name,
        source_url=winner.source_url,
        dimensions=dims,
        aggregate_score=round(aggregate, 4),
        exceeds_threshold=aggregate >= inspiration_min,
        clone_guard=clone_guard,
    )


def inspiration_threshold() -> float:
    return float(os.getenv("HACKFORGE_INSPIRATION_MIN", "0.30"))


def clone_dimension_threshold() -> float:
    return float(os.getenv("HACKFORGE_INSPIRATION_CLONE_DIM", "0.72"))


def build_inspiration_report(
    candidates: list[CandidateIdea],
    winners: list[VerifiedWinner],
    *,
    inspiration_min: float | None = None,
    training_cutoff: str | None = None,
    top_k: int = 3,
) -> InspirationReport:
    min_score = inspiration_min if inspiration_min is not None else inspiration_threshold()
    clone_min = clone_dimension_threshold()
    scored: list[CandidateInspirationScore] = []
    for candidate in candidates:
        matches = [
            score_against_winner(candidate, winner, inspiration_min=min_score, clone_dimension_min=clone_min)
            for winner in winners
        ]
        matches.sort(key=lambda row: -row.aggregate_score)
        nearest = matches[:top_k]
        max_aggregate = nearest[0].aggregate_score if nearest else 0.0
        clone_guard = any(row.clone_guard for row in nearest)
        flagged = max_aggregate >= min_score or clone_guard
        scored.append(
            CandidateInspirationScore(
                candidate_id=candidate.id,
                nearest_matches=nearest,
                max_aggregate=max_aggregate,
                clone_guard=clone_guard,
                flagged=flagged,
            )
        )
    return InspirationReport(
        inspiration_min=min_score,
        training_cutoff=training_cutoff or os.getenv("HACKFORGE_TRAINING_CUTOFF"),
        clone_dimension_min=clone_min,
        corpus_size=len(winners),
        candidates=scored,
    )


def inspiration_markdown(
    report: InspirationReport,
    *,
    titles_by_id: dict[str, str] | None = None,
) -> str:
    """Human-readable inspiration section for final-recommendation.md."""
    titles_by_id = titles_by_id or {}
    lines = [
        "## Winner inspiration (verified corpus)",
        "",
        f"- Corpus size: **{report.corpus_size}** verified winners",
        f"- Minimum aggregate alignment: **{report.inspiration_min:.0%}** (user + problem + mechanism mean)",
        f"- Training cutoff: **{report.training_cutoff or 'none'}**",
        "",
    ]
    for row in report.candidates:
        title = titles_by_id.get(row.candidate_id, row.candidate_id)
        lines.append(f"### {title} (`{row.candidate_id}`)")
        if not row.nearest_matches:
            lines.append("- No corpus matches after filters.")
            lines.append("")
            continue
        best = row.nearest_matches[0]
        lines.append(
            f"- Best pattern match: **{best.project_name}** "
            f"(aggregate {best.aggregate_score:.0%}) — [source]({best.source_url})"
        )
        lines.append(
            f"  - user {best.dimensions.user_alignment:.0%}, "
            f"problem {best.dimensions.problem_alignment:.0%}, "
            f"mechanism {best.dimensions.mechanism_alignment:.0%}"
        )
        if row.clone_guard:
            lines.append("- **Clone guard:** alignment too high on all three dimensions; treat as audit flag.")
        elif row.flagged:
            lines.append("- Meets inspiration threshold; adapt mechanism/demo for this track.")
        else:
            lines.append("- Below inspiration threshold vs nearest verified winner.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
