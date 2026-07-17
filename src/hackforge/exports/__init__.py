from __future__ import annotations

from hackforge.models import (
    CandidateIdea,
    CollisionReport,
    CompetitionBrief,
    EvaluationResult,
    FeasibilityReport,
)

from .landscape import build_idea_landscape as build_idea_landscape


def build_decision_dossier(
    brief: CompetitionBrief,
    primary: CandidateIdea,
    backup: CandidateIdea,
    evaluation: EvaluationResult,
    collisions: list[CollisionReport],
    feasibility: list[FeasibilityReport],
    rejected: list[CandidateIdea],
    red_team: dict,
) -> str:
    coll_p = next((c for c in collisions if c.candidate_id == primary.id), None)
    feas_p = next((f for f in feasibility if f.candidate_id == primary.id), None)

    lines = [
        f"# Final recommendation: {brief.name}",
        "",
        "## Primary concept",
        f"**Working title:** {primary.working_title}",
        f"**Internal id:** `{primary.id}`",
        f"**Primary user:** {primary.primary_user}",
        f"**Painful workflow:** {primary.painful_workflow}",
        f"**Imported mechanism:** {primary.imported_mechanism} _(from {primary.mechanism_origin})_",
        f"**Data sources:** {', '.join(primary.data_sources) or 'n/a'}",
        f"**Core computation:** {primary.core_computation}",
        f"**Last-mile action:** {primary.last_mile_action}",
        f"**Visible transformation:** {primary.visible_transformation}",
        f"**Killer demo:** {primary.killer_demo}",
        f"**Hard-to-fake advantage:** {primary.hard_to_fake_advantage}",
        f"**Sponsor dependency:** {primary.sponsor_dependency or 'none / intentionally unnecessary'}",
        "",
        "## Why this concept was selected",
        evaluation.recommendation.get("why", ""),
        "",
        "## Judge disagreement (do not average away)",
    ]
    if evaluation.disagreements:
        lines.extend(f"- {d}" for d in evaluation.disagreements)
    else:
        lines.append("- None (inspect vote table anyway)")
    lines += ["", "### Judge votes"]
    for v in evaluation.judge_votes:
        lines.append(f"- **{v.role}** → {v.preferred_blind_id}: {v.rationale}")

    lines += ["", "## Closest competing projects"]
    if coll_p:
        for a in coll_p.nearest_analogues:
            lines.append(f"- {a.name} ({a.source})")
        lines.append(f"- Collision risk: {coll_p.collision_risk}")
        lines.append(f"- Observable differentiator: {coll_p.observable_differentiator}")
        lines.append(f"- Differentiator substantive?: {coll_p.differentiator_is_substantive}")
    else:
        lines.append("- No collision report")

    lines += [
        "",
        "## Critical assumptions",
        f"- Data exists and is accessible: {', '.join(primary.data_sources) or 'UNSPECIFIED'}",
        f"- Delivery risk: {feas_p.delivery_risk if feas_p else 'unknown'}",
        f"- Technical risk note: {primary.technical_risk}",
    ]

    lines += [
        "",
        "## Technical proof sketch (not an architecture)",
        f"- Critical computation: {primary.core_computation}",
        f"- Required data: {', '.join(primary.data_sources)}",
        f"- Most dangerous dependency: {(feas_p.critical_dependencies[0] if feas_p and feas_p.critical_dependencies else primary.sponsor_dependency) or 'unknown'}",
        f"- Minimum demonstrable loop: {(feas_p.minimum_demonstrable_loop if feas_p else primary.killer_demo)}",
    ]

    lines += [
        "",
        "## Forty-eight-hour scope",
        f"- One user: {primary.primary_user}",
        f"- One workflow: {primary.painful_workflow}",
        f"- One demo moment: {primary.killer_demo}",
        "- Cut anything that does not improve the killer demo.",
    ]

    lines += [
        "",
        "## Primary failure risk",
        (feas_p.notes if feas_p else primary.kill_reason) or "Unspecified",
    ]

    lines += [
        "",
        "## Red team",
        f"- Conditional acceptance: {red_team.get('conditional_acceptance')}",
        f"- Prefer backup instead: {red_team.get('prefer_backup_instead')}",
        f"- Fatal flaws: {red_team.get('fatal_flaws')}",
        f"- Survive if: {red_team.get('survive_if')}",
    ]

    lines += [
        "",
        "## Backup concept",
        f"**{backup.working_title}** (`{backup.id}`)",
        f"- User: {backup.primary_user}",
        f"- Mechanism: {backup.imported_mechanism}",
        f"- Demo: {backup.killer_demo}",
    ]

    lines += ["", "## Rejected / not advanced"]
    for r in rejected[:20]:
        lines.append(f"- `{r.id}` — {r.working_title or r.primary_user}: {r.kill_reason or 'outcompeted / clustered'}")

    return "\n".join(lines)
