"""Decision-dossier rendering.

The dossier is the human-facing summary of why a concept won. It must not attribute
one concept's vote tally to another: the blind judge and the red team can disagree,
and when they do the primary concept is no longer the one the tally describes.
"""

from __future__ import annotations

from hackforge.exports import build_decision_dossier
from hackforge.models import CandidateIdea, CompetitionBrief, EvaluationResult, JudgeVote

JUDGE_TALLY = "Pairwise wins={'A': 5, 'D': 1}; votes={'A': 6}"
BACKUP_REASON = "The promoted concept has append-only correction lineage that is harder to fake."
FATAL_FLAW = "The trust score is not defensible without labeled truth."


def _idea(id: str, title: str) -> CandidateIdea:
    return CandidateIdea(
        id=id,
        working_title=title,
        primary_user="affordable-housing applicants",
        painful_workflow="a stale readiness packet value",
        current_workaround="manual edits with no record of who changed what",
        imported_mechanism="append-only provenance ledger",
        data_sources=["synthetic pay stubs"],
        core_computation="recompute declared dependents deterministically",
        last_mile_action="renter confirms the correction",
        visible_transformation="lineage chain regenerates the packet",
        killer_demo="correct one misread value and watch it propagate",
        hard_to_fake_advantage="immutable prior record plus dependency delta",
        collision_risk="low",
    )


def _evaluation() -> EvaluationResult:
    return EvaluationResult(
        candidates=[
            {"blind_id": "A", "internal_id": "concept-a"},
            {"blind_id": "D", "internal_id": "mut-d"},
        ],
        judge_votes=[
            JudgeVote(role="technical", preferred_blind_id="A", rationale="A wins on trust."),
            JudgeVote(role="impact", preferred_blind_id="A", rationale="A wins on reach."),
        ],
        recommendation={
            "primary_blind_id": "A",
            "backup_blind_id": "D",
            "why": JUDGE_TALLY,
        },
    )


def _dossier(*, swapped: bool) -> str:
    # After a swap the promoted concept (`mut-d`) is primary, while the judge's pick
    # (`concept-a`) stays the blind-judge winner.
    return build_decision_dossier(
        CompetitionBrief(name="Hack-Nation 6th Global AI Hackathon"),
        primary=_idea("mut-d" if swapped else "concept-a", "Rule Ledger"),
        backup=_idea("concept-a" if swapped else "mut-d", "Facility Trust Desk"),
        evaluation=_evaluation(),
        collisions=[],
        feasibility=[],
        rejected=[],
        red_team={
            "primary_id": "concept-a",
            "fatal_flaws": [FATAL_FLAW],
            "survive_if": ["Publish a reproducible schema profile."],
            "prefer_backup_instead": swapped,
            "backup_reason": BACKUP_REASON,
            "severity_acceptance": True,
        },
    )


def _section(text: str, heading: str) -> str:
    body = text.split(heading, 1)[1]
    return body.split("\n## ", 1)[0]


def test_red_team_override_is_stated_when_the_judge_pick_is_demoted() -> None:
    text = _dossier(swapped=True)

    section = _section(text, "## Why this concept was selected")
    assert "Red-team override" in section
    assert "`concept-a`" in section, "the overridden pick must be named"
    assert BACKUP_REASON in section, "the reason the promoted concept won belongs up top"
    assert JUDGE_TALLY in section


def test_vote_tally_is_attributed_to_the_overridden_pick_not_the_primary() -> None:
    section = _section(_dossier(swapped=True), "## Why this concept was selected")

    # The tally sits *below* a label naming whose tally it is, so a reader cannot take
    # concept-a's 6 votes as evidence for the concept named above.
    tally_at = section.index(JUDGE_TALLY)
    attribution = section[:tally_at]
    assert "for the overridden pick" in attribution
    assert "`concept-a`" in attribution


def test_judge_votes_are_marked_as_pre_swap_when_the_primary_changed() -> None:
    section = _section(_dossier(swapped=True), "### Judge votes")

    assert "before the red-team swap" in section
    assert "`concept-a`" in section


def test_judge_tally_remains_the_selection_reason_without_a_swap() -> None:
    text = _dossier(swapped=False)
    section = _section(text, "## Why this concept was selected")

    assert "Red-team override" not in section
    assert JUDGE_TALLY in section
    assert "### Judge votes" not in section
    # No swap means no caveat on the votes either.
    assert "before the red-team swap" not in text


def test_red_team_section_reports_current_fields() -> None:
    text = _dossier(swapped=True)
    section = _section(text, "## Red team")

    # `conditional_acceptance` was renamed to `severity_acceptance`; reading the old
    # name printed None for every run.
    assert "Conditional acceptance" not in text
    assert "Severity acceptance: True" in section
    assert "Reviewed concept: `concept-a`" in section
    # Flaws are bullets about the reviewed concept, not a repr()'d Python list.
    assert f"  - {FATAL_FLAW}" in section
    assert "['" not in section


def test_backup_reason_is_rendered_when_the_backup_stays_the_backup() -> None:
    section = _section(_dossier(swapped=False), "## Backup concept")

    assert BACKUP_REASON in section


def test_primary_section_names_the_promoted_concept_not_the_judge_pick() -> None:
    """The concept named at the top must be the promoted one, not the judge's pick."""
    primary = _section(_dossier(swapped=True), "## Primary concept")

    assert "**Internal id:** `mut-d`" in primary
    assert "concept-a" not in primary, "the overridden pick must not appear as the primary"
