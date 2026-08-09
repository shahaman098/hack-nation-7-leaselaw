from __future__ import annotations

import hashlib
import random
import re
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
from hackforge.paths import JUDGE_ROLES
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
        "build_window": brief.build_window,
        "team_size": brief.team_size,
        "mandatory_technologies": brief.mandatory_technologies(),
        "requirements": [requirement.model_dump() for requirement in brief.requirements if requirement.required],
        "submission_artifacts": brief.submission_artifacts,
        "demo_requirements": brief.demo_requirements,
        "data_requirements": brief.data_requirements,
        "candidates": [candidate.model_dump() for candidate in candidates],
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

    covered = {report.candidate_id for report in reports}
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
    for candidate in candidates:
        if candidate.id not in covered:
            reports.append(
                FeasibilityReport(
                    candidate_id=candidate.id,
                    delivery_risk="medium",
                    critical_dependencies=[candidate.sponsor_dependency] if candidate.sponsor_dependency else [],
                    non_fakeable_core=candidate.core_computation,
                    minimum_demonstrable_loop=candidate.minimum_demonstrable_loop or candidate.killer_demo,
                    notes="fixture-only fallback feasibility stub",
                )
            )
    return reports


def feasibility_markdown(reports: list[FeasibilityReport]) -> str:
    lines = ["# Feasibility analysis", ""]
    for report in reports:
        lines.append(f"## {report.candidate_id}")
        lines.append(f"- Delivery risk: **{report.delivery_risk}**")
        lines.append(f"- Kill?: {report.kill_recommendation}")
        lines.append(f"- Non-fakeable core: {report.non_fakeable_core}")
        lines.append(f"- Minimum completion/proof loop: {report.minimum_demonstrable_loop}")
        lines.append(f"- Dependencies: {', '.join(report.critical_dependencies)}")
        lines.append(f"- Notes: {report.notes}")
        lines.append("")
    return "\n".join(lines)


def blind_judge(
    provider: LLMProvider,
    brief: CompetitionBrief,
    finalists: list[CandidateIdea],
    collisions: list[CollisionReport],
    feasibility: list[FeasibilityReport],
) -> EvaluationResult:
    if not finalists:
        raise ValueError("blind_judge requires at least one finalist")

    shuffled = sorted(finalists, key=lambda candidate: candidate.id)
    seed_material = brief.name + "|" + "|".join(candidate.id for candidate in shuffled)
    random.Random(int(hashlib.sha256(seed_material.encode()).hexdigest()[:16], 16)).shuffle(shuffled)
    blind_map = {chr(ord("A") + index): candidate for index, candidate in enumerate(shuffled)}
    collision_by = {report.candidate_id: report for report in collisions}
    feasibility_by = {report.candidate_id: report for report in feasibility}

    anonymized = []
    for blind_id, candidate in blind_map.items():
        anonymized.append(
            {
                "blind_id": blind_id,
                "primary_user": candidate.primary_user,
                "painful_workflow": candidate.painful_workflow,
                "imported_mechanism": candidate.imported_mechanism,
                "data_sources": candidate.data_sources,
                "core_computation": candidate.core_computation,
                "last_mile_action": candidate.last_mile_action,
                "visible_transformation": candidate.visible_transformation,
                "killer_demo": candidate.killer_demo,
                "hard_to_fake_advantage": candidate.hard_to_fake_advantage,
                "technology_roles": candidate.technology_roles,
                "requirement_satisfaction": candidate.requirement_satisfaction,
                "delivery_plan": candidate.minimum_demonstrable_loop,
                "track_fit": candidate.track_fit,
                "collision_risk": (
                    collision_by[candidate.id].collision_risk
                    if candidate.id in collision_by
                    else candidate.collision_risk
                ),
                "delivery_risk": (
                    feasibility_by[candidate.id].delivery_risk
                    if candidate.id in feasibility_by
                    else "unknown"
                ),
            }
        )

    criteria = [criterion.model_dump() for criterion in brief.judging_criteria]
    constraints = {
        "tracks": brief.tracks,
        "mandatory_technologies": brief.mandatory_technologies(),
        "requirements": [requirement.model_dump() for requirement in brief.requirements if requirement.required],
        "submission_artifacts": brief.submission_artifacts,
        "demo_requirements": brief.demo_requirements,
        "data_requirements": brief.data_requirements,
        "build_window": brief.build_window,
        "deadline": brief.deadline,
        "team_size": brief.team_size,
    }

    template, _ = load_prompt("blind-judge")
    votes: list[JudgeVote] = []
    for role in JUDGE_ROLES:
        system = render_prompt(template, {"JUDGE_ROLE": role})
        vote_schema = _vote_schema(list(blind_map))
        raw = provider.complete_json(
            system,
            str(
                {
                    "official_criteria": criteria,
                    "competition_constraints": constraints,
                    "candidates": anonymized,
                }
            ),
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

    hard_gates = _candidate_hard_gates(blind_map, collision_by, feasibility_by)
    disagreements = _surface_disagreements(votes)
    pairwise = _real_pairwise(
        provider,
        template,
        criteria,
        constraints,
        anonymized,
        votes,
        list(blind_map),
    )
    vote_counts = Counter(vote.preferred_blind_id for vote in votes)
    pairwise_wins = Counter(result.winner for result in pairwise)

    ordered = sorted(
        blind_map,
        key=lambda blind_id: (
            -pairwise_wins[blind_id],
            -_weighted_official_score(votes, blind_id, brief),
            -vote_counts[blind_id],
            blind_id,
        ),
    )
    primary = next(
        (
            blind_id
            for blind_id in ordered
            if all(gate.get("passed", True) for gate in hard_gates.get(blind_id, {}).values())
        ),
        ordered[0],
    )
    backup = next((blind_id for blind_id in ordered if blind_id != primary), primary)

    return EvaluationResult(
        candidates=[
            {"blind_id": blind_id, "internal_id": candidate.id}
            for blind_id, candidate in blind_map.items()
        ],
        hard_gates=hard_gates,
        judge_votes=votes,
        disagreements=disagreements,
        pairwise=pairwise,
        recommendation={
            "primary_blind_id": primary,
            "backup_blind_id": backup,
            "why": (
                f"Pairwise wins={dict(pairwise_wins)}; votes={dict(vote_counts)}; "
                "official competition criteria and their parsed weights/priorities determine ordering; "
                f"disagreements={len(disagreements)}"
            ),
        },
    )


def _candidate_hard_gates(
    blind_map: dict[str, CandidateIdea],
    collision_by: dict[str, CollisionReport],
    feasibility_by: dict[str, FeasibilityReport],
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for blind_id, candidate in blind_map.items():
        gates: dict[str, Any] = {}
        for result in candidate.gate_results:
            gates[result.gate] = {
                "passed": result.status in {"pass", "not_applicable"},
                "status": result.status,
                "notes": result.reason,
            }
        collision = collision_by.get(candidate.id)
        gates["collision_risk_acceptable"] = {
            "passed": not (
                collision
                and collision.collision_risk == "high"
                and collision.kill_recommendation
            ),
            "notes": collision.notes if collision else candidate.collision_risk,
        }
        feasibility = feasibility_by.get(candidate.id)
        gates["independent_feasibility"] = {
            "passed": not (
                feasibility
                and feasibility.delivery_risk == "high"
                and feasibility.kill_recommendation
            ),
            "notes": feasibility.notes if feasibility else "no independent kill recommendation",
        }
        output[blind_id] = gates
    return output


def _surface_disagreements(votes: list[JudgeVote]) -> list[str]:
    by_choice: dict[str, list[str]] = {}
    for vote in votes:
        by_choice.setdefault(vote.preferred_blind_id, []).append(vote.role)
    if len(by_choice) <= 1:
        return []
    parts = [f"{blind_id}: {', '.join(roles)}" for blind_id, roles in sorted(by_choice.items())]
    return [
        "Judge disagreement — " + " | ".join(parts),
        "Inspect the official-criteria tradeoffs rather than averaging away disagreement.",
    ]


def _real_pairwise(
    provider: LLMProvider,
    template: str,
    criteria: list[dict[str, Any]],
    constraints: dict[str, Any],
    anonymized: list[dict[str, Any]],
    votes: list[JudgeVote],
    ids: list[str],
) -> list[PairwiseResult]:
    pairs = [[left, right] for index, left in enumerate(ids) for right in ids[index + 1 :]]
    if not pairs:
        return []
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
                        "pair": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
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
        + "\nCompare every supplied pair directly using only the supplied official competition criteria "
        "and applicable requirements. Do not import a universal technical, demo, sponsor, or impact "
        "tie-breaker. Return {comparisons:[...]} only."
    )
    try:
        raw = provider.complete_json(
            system,
            str(
                {
                    "official_criteria": criteria,
                    "competition_constraints": constraints,
                    "candidates": anonymized,
                    "pairs": pairs,
                }
            ),
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
        if not isinstance(row, dict):
            continue
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

    vote_counts = Counter(vote.preferred_blind_id for vote in votes)
    for left, right in pairs:
        if (left, right) in seen:
            continue
        left_key = (_score_from_votes(votes, left), vote_counts[left], -ord(left[0]))
        right_key = (_score_from_votes(votes, right), vote_counts[right], -ord(right[0]))
        winner = left if left_key >= right_key else right
        results.append(
            PairwiseResult(
                pair=[left, right],
                winner=winner,
                reason=(
                    "Deterministic fallback from official-criteria judge scores and independent votes: "
                    f"{left}={left_key[:2]} vs {right}={right_key[:2]}"
                ),
            )
        )
    return results


def _weighted_official_score(
    votes: list[JudgeVote],
    blind_id: str,
    brief: CompetitionBrief,
) -> float:
    score_sets = [_scores_for_candidate(vote, blind_id) for vote in votes]
    score_sets = [scores for scores in score_sets if scores]
    if not score_sets:
        return 0.0

    criteria = brief.judging_criteria
    values: list[float] = []
    for scores in score_sets:
        if criteria:
            weighted_total = 0.0
            total_weight = 0.0
            for criterion in criteria:
                score = _criterion_score(scores, criterion.name)
                if score is None:
                    continue
                weight = _criterion_weight(criterion.weight_or_priority)
                weighted_total += score * weight
                total_weight += weight
            if total_weight:
                values.append(weighted_total / total_weight)
                continue
        numeric = [float(value) for value in scores.values() if isinstance(value, (int, float))]
        if numeric:
            values.append(sum(numeric) / len(numeric))
    return sum(values) / len(values) if values else 0.0


def _score_from_votes(votes: list[JudgeVote], blind_id: str) -> float:
    score_sets = [_scores_for_candidate(vote, blind_id) for vote in votes]
    numeric = [
        float(value)
        for scores in score_sets
        for value in scores.values()
        if isinstance(value, (int, float))
    ]
    return sum(numeric) / len(numeric) if numeric else 0.0


def _scores_for_candidate(vote: JudgeVote, blind_id: str) -> dict[str, Any]:
    raw = vote.scores_by_official_criteria
    nested = raw.get(blind_id)
    if isinstance(nested, dict):
        return nested
    return raw if vote.preferred_blind_id == blind_id else {}


def _criterion_score(scores: dict[str, Any], criterion_name: str) -> float | None:
    wanted = _norm(criterion_name)
    for key, value in scores.items():
        if not isinstance(value, (int, float)):
            continue
        current = _norm(key)
        if current == wanted or current in wanted or wanted in current:
            return float(value)
    return None


def _criterion_weight(raw: str) -> float:
    text = raw.strip().lower()
    percent = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if percent:
        return max(0.0001, float(percent.group(1)) / 100.0)
    number = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", text)
    if number:
        return max(0.0001, float(number.group(1)))
    labels = {"highest": 4.0, "critical": 4.0, "high": 3.0, "medium": 2.0, "low": 1.0}
    for label, weight in labels.items():
        if label in text:
            return weight
    return 1.0


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def red_team_check(
    provider: LLMProvider,
    primary: CandidateIdea,
    backup: CandidateIdea,
) -> dict[str, Any]:
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
    if isinstance(provider, DryRunProvider) and "severity_acceptance" not in raw:
        raw["severity_acceptance"] = bool(raw.get("conditional_acceptance", True))
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


def _vote_schema(blind_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "role": {"type": "string"},
            "preferred_blind_id": {"type": "string", "enum": blind_ids},
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
                        "critical_dependencies": {
                            "type": "array",
                            "maxItems": 3,
                            "items": {"type": "string"},
                        },
                        "fakeable_parts": {
                            "type": "array",
                            "maxItems": 3,
                            "items": {"type": "string"},
                        },
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
