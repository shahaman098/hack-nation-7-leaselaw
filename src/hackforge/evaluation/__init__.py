from __future__ import annotations

from collections import Counter
from typing import Any

from hackforge.models import (
    CandidateIdea,
    CollisionReport,
    CompetitionBrief,
    EvaluationResult,
    FeasibilityReport,
    JudgeVote,
    PairwiseResult,
)
from hackforge.paths import HARD_GATES, JUDGE_ROLES
from hackforge.providers import LLMProvider
from hackforge.utils import load_prompt, render_prompt


def review_feasibility(
    provider: LLMProvider,
    candidates: list[CandidateIdea],
    brief: CompetitionBrief,
) -> list[FeasibilityReport]:
    template, _ = load_prompt("feasibility")
    payload = {
        "deadline": brief.deadline,
        "team_size": brief.team_size,
        "required_tech": brief.required_or_encouraged_tech,
        "candidates": [c.model_dump() for c in candidates],
    }
    raw = provider.complete_json(template, str(payload))
    items = raw if isinstance(raw, list) else raw.get("reports") or []
    reports: list[FeasibilityReport] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        reports.append(
            FeasibilityReport(
                candidate_id=str(item.get("candidate_id") or ""),
                delivery_risk=item.get("delivery_risk") or "medium",
                critical_dependencies=list(item.get("critical_dependencies") or []),
                fakeable_parts=list(item.get("fakeable_parts") or []),
                non_fakeable_core=str(item.get("non_fakeable_core") or ""),
                minimum_demonstrable_loop=str(item.get("minimum_demonstrable_loop") or ""),
                kill_recommendation=bool(item.get("kill_recommendation")),
                notes=str(item.get("notes") or ""),
            )
        )
    covered = {r.candidate_id for r in reports}
    for c in candidates:
        if c.id not in covered:
            reports.append(
                FeasibilityReport(
                    candidate_id=c.id,
                    delivery_risk="medium",
                    critical_dependencies=[c.sponsor_dependency] if c.sponsor_dependency else [],
                    non_fakeable_core=c.core_computation,
                    minimum_demonstrable_loop=c.killer_demo,
                    notes="fallback feasibility stub",
                )
            )
    return reports


def feasibility_markdown(reports: list[FeasibilityReport]) -> str:
    lines = ["# Feasibility analysis", ""]
    for r in reports:
        lines.append(f"## {r.candidate_id}")
        lines.append(f"- Delivery risk: **{r.delivery_risk}**")
        lines.append(f"- Kill?: {r.kill_recommendation}")
        lines.append(f"- Non-fakeable core: {r.non_fakeable_core}")
        lines.append(f"- Min demo loop: {r.minimum_demonstrable_loop}")
        lines.append(f"- Dependencies: {', '.join(r.critical_dependencies)}")
        lines.append(f"- Notes: {r.notes}")
        lines.append("")
    return "\n".join(lines)


def blind_judge(
    provider: LLMProvider,
    brief: CompetitionBrief,
    finalists: list[CandidateIdea],
    collisions: list[CollisionReport],
    feasibility: list[FeasibilityReport],
) -> EvaluationResult:
    blind_map = {chr(ord("A") + i): c for i, c in enumerate(finalists)}
    reverse = {c.id: bid for bid, c in blind_map.items()}
    coll_by = {r.candidate_id: r for r in collisions}
    feas_by = {r.candidate_id: r for r in feasibility}

    anonymized = []
    for bid, c in blind_map.items():
        anonymized.append(
            {
                "blind_id": bid,
                "primary_user": c.primary_user,
                "painful_workflow": c.painful_workflow,
                "imported_mechanism": c.imported_mechanism,
                "data_sources": c.data_sources,
                "core_computation": c.core_computation,
                "last_mile_action": c.last_mile_action,
                "visible_transformation": c.visible_transformation,
                "killer_demo": c.killer_demo,
                "hard_to_fake_advantage": c.hard_to_fake_advantage,
                "collision_risk": (coll_by.get(c.id).collision_risk if c.id in coll_by else c.collision_risk),
                "delivery_risk": (feas_by.get(c.id).delivery_risk if c.id in feas_by else "unknown"),
                "track_hints": brief.tracks,
            }
        )

    criteria = [c.model_dump() for c in brief.judging_criteria]
    template, _ = load_prompt("blind-judge")
    votes: list[JudgeVote] = []
    for role in JUDGE_ROLES:
        system = render_prompt(template, {"JUDGE_ROLE": role})
        raw = provider.complete_json(
            system,
            f"Official criteria: {criteria}\nCandidates: {anonymized}",
        )
        if not isinstance(raw, dict):
            raw = {"preferred_blind_id": "A", "rationale": "malformed judge output", "role": role}
        preferred = str(raw.get("preferred_blind_id") or "A").upper()
        if preferred not in blind_map:
            preferred = next(iter(blind_map))
        votes.append(
            JudgeVote(
                role=role,
                preferred_blind_id=preferred,
                rationale=str(raw.get("rationale") or ""),
                scores_by_official_criteria=dict(raw.get("scores_by_official_criteria") or {}),
                hard_gate_failures=list(raw.get("hard_gate_failures") or []),
                demo_failure_risk=raw.get("demo_failure_risk") or "medium",
            )
        )

    hard_gates = _evaluate_hard_gates(finalists, coll_by, feas_by, reverse)
    disagreements = _surface_disagreements(votes)
    pairwise = _pairwise(votes, list(blind_map.keys()))
    counts = Counter(v.preferred_blind_id for v in votes)
    # Prefer candidate with most votes that also passes hard gates; preserve outliers if tied
    ordered = sorted(blind_map.keys(), key=lambda b: (-counts[b], b))
    primary = ordered[0]
    for bid in ordered:
        gates = hard_gates.get(bid, {})
        if all(g.get("passed", True) for g in gates.values()):
            primary = bid
            break
    backup = next((b for b in ordered if b != primary), ordered[0])

    return EvaluationResult(
        candidates=[{"blind_id": bid, "internal_id": c.id} for bid, c in blind_map.items()],
        hard_gates=hard_gates,
        judge_votes=votes,
        disagreements=disagreements,
        pairwise=pairwise,
        recommendation={
            "primary_blind_id": primary,
            "backup_blind_id": backup,
            "why": f"Votes={dict(counts)}; disagreements={len(disagreements)}",
        },
    )


def _evaluate_hard_gates(
    finalists: list[CandidateIdea],
    coll_by: dict[str, CollisionReport],
    feas_by: dict[str, FeasibilityReport],
    reverse: dict[str, str],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for c in finalists:
        bid = reverse[c.id]
        coll = coll_by.get(c.id)
        feas = feas_by.get(c.id)
        gates = {
            "demonstrable_core": {
                "passed": bool(c.killer_demo),
                "notes": c.killer_demo or "missing killer demo",
            },
            "real_computation_or_action": {
                "passed": bool(c.core_computation and c.last_mile_action),
                "notes": c.core_computation,
            },
            "data_accessible": {
                "passed": bool(c.data_sources),
                "notes": ", ".join(c.data_sources) or "no named data",
            },
            "specific_track_fit": {
                "passed": True,
                "notes": "assessed against brief tracks in judge prompt",
            },
            "sponsor_tech_material_or_explicitly_unnecessary": {
                "passed": True,
                "notes": c.sponsor_dependency or "explicitly none",
            },
            "core_loop_deliverable": {
                "passed": not (feas and feas.kill_recommendation),
                "notes": feas.notes if feas else "",
            },
            "clear_60s_transformation": {
                "passed": bool(c.visible_transformation),
                "notes": c.visible_transformation,
            },
            "collision_risk_acceptable": {
                "passed": not (coll and coll.collision_risk == "high" and coll.kill_recommendation),
                "notes": coll.collision_risk if coll else c.collision_risk,
            },
        }
        # Ensure all configured gates present
        for g in HARD_GATES:
            gates.setdefault(g, {"passed": True, "notes": ""})
        out[bid] = gates
    return out


def _surface_disagreements(votes: list[JudgeVote]) -> list[str]:
    by_choice: dict[str, list[str]] = {}
    for v in votes:
        by_choice.setdefault(v.preferred_blind_id, []).append(v.role)
    if len(by_choice) <= 1:
        return []
    parts = [f"{bid}: {', '.join(roles)}" for bid, roles in sorted(by_choice.items())]
    return [
        "Judge disagreement — " + " | ".join(parts),
        "Do not average automatically; inspect tradeoffs (novelty vs demo reliability vs sponsor fit).",
    ]


def _pairwise(votes: list[JudgeVote], ids: list[str]) -> list[PairwiseResult]:
    counts = Counter(v.preferred_blind_id for v in votes)
    results = []
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            winner = a if counts[a] >= counts[b] else b
            results.append(
                PairwiseResult(
                    pair=[a, b],
                    winner=winner,
                    reason=f"Vote tally {a}={counts[a]} vs {b}={counts[b]}",
                )
            )
    return results


def red_team_check(provider: LLMProvider, primary: CandidateIdea, backup: CandidateIdea) -> dict[str, Any]:
    template, _ = load_prompt("red-team")
    raw = provider.complete_json(
        template,
        f"Primary: {primary.model_dump()}\nBackup: {backup.model_dump()}",
    )
    if not isinstance(raw, dict):
        return {"primary_id": primary.id, "fatal_flaws": [], "conditional_acceptance": True}
    return raw
