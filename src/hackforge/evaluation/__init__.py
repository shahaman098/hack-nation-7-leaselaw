from __future__ import annotations

import hashlib
import random
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
from hackforge.providers import DryRunProvider, LLMProvider
from hackforge.utils import load_prompt, render_prompt

from .gates import REQUIRED_GATES as REQUIRED_GATES
from .gates import evaluate_gates as evaluate_gates
from .gates import gate_failures as gate_failures
from .gates import passes_gates as passes_gates


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
    schema = None if isinstance(provider, DryRunProvider) else _feasibility_schema(len(candidates))
    raw = provider.complete_json(template, str(payload), schema=schema)
    items = raw if isinstance(raw, list) else raw.get("reports") or []
    if not isinstance(items, list):
        raise RuntimeError("feasibility review returned a non-list reports payload")
    reports: list[FeasibilityReport] = []
    required_fields = {
        "candidate_id",
        "delivery_risk",
        "critical_dependencies",
        "fakeable_parts",
        "non_fakeable_core",
        "minimum_demonstrable_loop",
        "kill_recommendation",
        "notes",
    }
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            if not isinstance(provider, DryRunProvider):
                raise RuntimeError(f"feasibility review row {index} was not an object")
            continue
        missing_fields = required_fields - set(item)
        if missing_fields and not isinstance(provider, DryRunProvider):
            raise RuntimeError(
                f"feasibility review row {index} omitted fields {sorted(missing_fields)}; "
                "no default values were inserted"
            )
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
    if len(covered) != len(reports) and not isinstance(provider, DryRunProvider):
        raise RuntimeError("feasibility review returned duplicate candidate ids")
    expected = {candidate.id for candidate in candidates}
    unexpected = covered - expected
    if unexpected and not isinstance(provider, DryRunProvider):
        raise RuntimeError(f"feasibility review returned unknown candidate ids: {sorted(unexpected)}")
    missing = expected - covered
    if missing and not isinstance(provider, DryRunProvider):
        raise RuntimeError(
            f"feasibility review omitted candidate ids {sorted(missing)}; no fallback reports were generated"
        )
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
    shuffled = sorted(finalists, key=lambda candidate: candidate.id)
    seed_material = brief.name + "|" + "|".join(candidate.id for candidate in shuffled)
    random.Random(int(hashlib.sha256(seed_material.encode()).hexdigest()[:16], 16)).shuffle(shuffled)
    blind_map = {chr(ord("A") + i): c for i, c in enumerate(shuffled)}
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
                "collision_risk": coll_by[c.id].collision_risk if c.id in coll_by else c.collision_risk,
                "delivery_risk": feas_by[c.id].delivery_risk if c.id in feas_by else "unknown",
                "track_hints": brief.tracks,
            }
        )

    criteria = [c.model_dump() for c in brief.judging_criteria]
    template, _ = load_prompt("blind-judge")
    votes: list[JudgeVote] = []
    for role in JUDGE_ROLES:
        system = render_prompt(template, {"JUDGE_ROLE": role})
        vote_schema = {
            "type": "object",
            "properties": {
                "role": {"type": "string"},
                "preferred_blind_id": {"type": "string", "enum": list(blind_map)},
                "rationale": {"type": "string"},
                "scores_by_official_criteria": {"type": "object"},
                "hard_gate_failures": {"type": "array", "items": {"type": "string"}},
                "demo_failure_risk": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": [
                "role",
                "preferred_blind_id",
                "rationale",
                "scores_by_official_criteria",
                "hard_gate_failures",
                "demo_failure_risk",
            ],
            "additionalProperties": False,
        }
        raw = provider.complete_json(
            system,
            f"Official criteria: {criteria}\nCandidates: {anonymized}",
            schema=None if isinstance(provider, DryRunProvider) else vote_schema,
        )
        if not isinstance(raw, dict):
            raise RuntimeError(f"{role} judge returned a non-object response")
        required_vote_fields = {
            "preferred_blind_id",
            "rationale",
            "scores_by_official_criteria",
            "hard_gate_failures",
            "demo_failure_risk",
        }
        missing_vote_fields = required_vote_fields - set(raw)
        if missing_vote_fields and not isinstance(provider, DryRunProvider):
            raise RuntimeError(f"{role} judge omitted fields {sorted(missing_vote_fields)}")
        preferred = str(raw.get("preferred_blind_id") or "A").upper()
        if preferred not in blind_map:
            raise RuntimeError(f"{role} judge selected unknown blind id {preferred!r}")
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
    pairwise = _real_pairwise(provider, template, criteria, anonymized, votes, list(blind_map.keys()))
    counts = Counter(v.preferred_blind_id for v in votes)
    pairwise_wins = Counter(result.winner for result in pairwise)
    ordered = sorted(
        blind_map.keys(),
        key=lambda bid: (
            -pairwise_wins[bid],
            -_weighted_official_score(votes, bid, brief),
            -_technical_score(votes, bid),
            -counts[bid],
            bid,
        ),
    )
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
            "why": (
                f"Pairwise wins={dict(pairwise_wins)}; votes={dict(counts)}; "
                "official criteria applied with technical implementation as tie-breaker; "
                f"disagreements={len(disagreements)}"
            ),
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
            "demonstrable_core": {"passed": bool(c.killer_demo), "notes": c.killer_demo or "missing killer demo"},
            "real_computation_or_action": {
                "passed": bool(c.core_computation and c.last_mile_action),
                "notes": c.core_computation,
            },
            "data_accessible": {"passed": bool(c.data_sources), "notes": ", ".join(c.data_sources) or "no named data"},
            "specific_track_fit": {"passed": True, "notes": "assessed against brief tracks in judge prompt"},
            "sponsor_tech_material_or_explicitly_unnecessary": {
                "passed": True,
                "notes": c.sponsor_dependency or "explicitly none",
            },
            "core_loop_deliverable": {
                "passed": not (feas and feas.kill_recommendation),
                "notes": feas.notes if feas else "",
            },
            "clear_60s_transformation": {"passed": bool(c.visible_transformation), "notes": c.visible_transformation},
            "collision_risk_acceptable": {
                "passed": not (coll and coll.collision_risk == "high" and coll.kill_recommendation),
                "notes": coll.collision_risk if coll else c.collision_risk,
            },
        }
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


def _real_pairwise(
    provider: LLMProvider,
    template: str,
    criteria: list[dict[str, Any]],
    anonymized: list[dict[str, Any]],
    votes: list[JudgeVote],
    ids: list[str],
) -> list[PairwiseResult]:
    pairs = [[a, b] for index, a in enumerate(ids) for b in ids[index + 1 :]]
    schema = {
        "type": "object",
        "properties": {
            "comparisons": {
                "type": "array",
                "minItems": len(pairs),
                "maxItems": len(pairs),
                "items": {
                    "type": "object",
                    "properties": {
                        "pair": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2},
                        "winner": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["pair", "winner", "reason"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["comparisons"],
        "additionalProperties": False,
    }
    system = (
        template.replace("{{JUDGE_ROLE}}", "pairwise-comparator")
        + "\nCompare every supplied pair directly using only the supplied official competition criteria. "
        "Do not infer pair winners from an overall ranking. Return {comparisons:[...]} only."
    )
    try:
        raw = provider.complete_json(
            system,
            str({"official_criteria": criteria, "candidates": anonymized, "pairs": pairs}),
            schema=schema,
            retries=1,
        )
        rows = raw.get("comparisons") if isinstance(raw, dict) else []
    except Exception:
        if not isinstance(provider, DryRunProvider):
            raise
        rows = []
    results: list[PairwiseResult] = []
    expected = {tuple(pair) for pair in pairs}
    seen: set[tuple[str, str]] = set()
    for row in rows or []:
        pair = [str(item).upper() for item in row.get("pair") or []]
        if len(pair) != 2 or tuple(pair) not in expected or tuple(pair) in seen:
            continue
        winner = str(row.get("winner") or "").upper()
        if winner not in pair:
            continue
        seen.add((pair[0], pair[1]))
        results.append(PairwiseResult(pair=pair, winner=winner, reason=str(row.get("reason") or "")))
    if len(results) == len(pairs):
        return results

    if not isinstance(provider, DryRunProvider):
        missing = [list(pair) for pair in expected - seen]
        raise RuntimeError(
            f"pairwise judge returned {len(results)} valid comparisons; required {len(pairs)}; "
            f"missing={missing}; no deterministic fallback was used"
        )

    counts = Counter(v.preferred_blind_id for v in votes)
    for a, b in pairs:
        if (a, b) in seen:
            continue
        a_key = (counts[a], _technical_score(votes, a), -ord(a[0]))
        b_key = (counts[b], _technical_score(votes, b), -ord(b[0]))
        winner = a if a_key >= b_key else b
        results.append(
            PairwiseResult(
                pair=[a, b],
                winner=winner,
                reason=f"Deterministic fallback: independent votes {a}={counts[a]} vs {b}={counts[b]}",
            )
        )
    return results


def _weighted_official_score(votes: list[JudgeVote], blind_id: str, brief: CompetitionBrief) -> float:
    del brief
    score_sets = [_scores_for_candidate(vote, blind_id) for vote in votes]
    score_sets = [scores for scores in score_sets if scores]
    if not score_sets:
        return 0.0
    totals = []
    for scores in score_sets:
        numeric = [float(value) for value in scores.values() if isinstance(value, (int, float))]
        if numeric:
            totals.append(sum(numeric) / len(numeric))
    return sum(totals) / len(totals) if totals else 0.0


def _technical_score(votes: list[JudgeVote], blind_id: str) -> float:
    values = [_criterion_value(_scores_for_candidate(vote, blind_id), "implementation") for vote in votes]
    nonzero = [value for value in values if value]
    return sum(nonzero) / len(nonzero) if nonzero else 0.0


def _scores_for_candidate(vote: JudgeVote, blind_id: str) -> dict[str, Any]:
    raw = vote.scores_by_official_criteria
    nested = raw.get(blind_id)
    if isinstance(nested, dict):
        return nested
    return raw if vote.preferred_blind_id == blind_id else {}


def _criterion_value(scores: dict[str, Any], category: str) -> float:
    aliases = {
        "implementation": ("implementation", "technical"),
        "design": ("design", "demo", "experience"),
        "impact": ("impact", "applicability", "real-world"),
        "idea": ("idea", "originality", "quality"),
    }
    for key, value in scores.items():
        if any(alias in key.lower() for alias in aliases[category]) and isinstance(value, (int, float)):
            return float(value)
    return 0.0


def red_team_check(provider: LLMProvider, primary: CandidateIdea, backup: CandidateIdea) -> dict[str, Any]:
    template, _ = load_prompt("red-team")
    schema = {
        "type": "object",
        "properties": {
            "primary_id": {"type": "string"},
            "fatal_flaws": {"type": "array", "items": {"type": "string"}},
            "survive_if": {"type": "array", "items": {"type": "string"}},
            "prefer_backup_instead": {"type": "boolean"},
            "backup_reason": {"type": "string"},
            "severity_acceptance": {"type": "boolean"},
        },
        "required": [
            "primary_id",
            "fatal_flaws",
            "survive_if",
            "prefer_backup_instead",
            "backup_reason",
            "severity_acceptance",
        ],
        "additionalProperties": False,
    }
    raw = provider.complete_json(
        template,
        f"Primary: {primary.model_dump()}\nBackup: {backup.model_dump()}",
        schema=None if isinstance(provider, DryRunProvider) else schema,
    )
    if not isinstance(raw, dict):
        raise RuntimeError("red-team review returned a non-object response")
    required = {
        "primary_id",
        "fatal_flaws",
        "survive_if",
        "prefer_backup_instead",
        "backup_reason",
        "severity_acceptance",
    }
    missing = required - set(raw)
    if missing and not isinstance(provider, DryRunProvider):
        raise RuntimeError(f"red-team review omitted fields {sorted(missing)}")
    return raw


def _feasibility_schema(count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "reports": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": {
                    "type": "object",
                    "properties": {
                        "candidate_id": {"type": "string"},
                        "delivery_risk": {"type": "string", "enum": ["low", "medium", "high"]},
                        "critical_dependencies": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
                        "fakeable_parts": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
                        "non_fakeable_core": {"type": "string"},
                        "minimum_demonstrable_loop": {"type": "string"},
                        "kill_recommendation": {"type": "boolean"},
                        "notes": {"type": "string"},
                    },
                    "required": [
                        "candidate_id",
                        "delivery_risk",
                        "critical_dependencies",
                        "fakeable_parts",
                        "non_fakeable_core",
                        "minimum_demonstrable_loop",
                        "kill_recommendation",
                        "notes",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["reports"],
        "additionalProperties": False,
    }
