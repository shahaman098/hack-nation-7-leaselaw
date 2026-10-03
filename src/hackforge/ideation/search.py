from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from hackforge.models import (
    CandidateIdea,
    CompetitionBrief,
    EvidenceSource,
    IdeaLineage,
    MechanismCard,
    NoveltyVector,
    OpportunityCard,
)
from hackforge.providers import DryRunProvider, LLMProvider
from hackforge.utils import env_flag, load_prompt, slugify


@dataclass(frozen=True)
class SearchProfile:
    opportunities: int
    mechanisms: int
    initial_concepts: int
    mutation_rounds: int
    mutations_per_round: int
    collision_shortlist: int
    judged_finalists: int

    @property
    def evaluated_concepts(self) -> int:
        return self.initial_concepts + self.mutation_rounds * self.mutations_per_round


SEARCH_PROFILES = {
    "fast": SearchProfile(4, 4, 6, 1, 2, 4, 4),
    "balanced": SearchProfile(24, 24, 32, 2, 8, 12, 6),
    "exhaustive": SearchProfile(40, 40, 64, 3, 12, 18, 8),
}


def get_search_profile(name: str) -> SearchProfile:
    try:
        return SEARCH_PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown search profile: {name}") from exc


def discover_opportunities(
    provider: LLMProvider,
    brief: CompetitionBrief,
    evidence: list[EvidenceSource],
    count: int,
    winner_patterns: dict[str, Any] | None = None,
) -> list[OpportunityCard]:
    template, _ = load_prompt("opportunity-discovery")
    rows: list[Any] = []
    batch_size = count if isinstance(provider, DryRunProvider) else 4
    for start in range(0, count, batch_size):
        batch_count = min(batch_size, count - start)
        schema = _array_wrapper_schema("opportunities", _opportunity_schema(), count=batch_count)
        payload = {
            "count": batch_count,
            "batch": {"start": start, "total": count},
            "competition": brief.model_dump(),
            "evidence_catalog": [
                {"id": source.id, "title": source.title, "url": source.url, "excerpt": source.excerpt[:1800]}
                for source in evidence
                if source.fetch_status == "ok"
            ],
        }
        if winner_patterns:
            payload["winner_patterns"] = winner_patterns
        try:
            raw = provider.complete_json(template, str(payload), schema=schema)
            value = raw.get("opportunities") if isinstance(raw, dict) else None
            rows.extend(value if isinstance(value, list) else [])
        except Exception:
            if not isinstance(provider, DryRunProvider):
                raise

    cards: list[OpportunityCard] = []
    for index, row in enumerate(rows or []):
        if not isinstance(row, dict) or _looks_like_product(row):
            if not isinstance(provider, DryRunProvider):
                raise RuntimeError(
                    f"opportunity discovery returned an invalid product-shaped row at index {index}"
                )
            continue
        cards.append(
            OpportunityCard(
                id=str(row.get("id") or f"opp-{index + 1:02d}"),
                user_class=str(row.get("user_class") or "competition stakeholder"),
                painful_workflow=str(row.get("painful_workflow") or ""),
                unmet_need=str(row.get("unmet_need") or ""),
                evidence_ids=list(row.get("evidence_ids") or []),
                track=str(row.get("track") or ""),
                why_now=str(row.get("why_now") or ""),
                unresolved_claims=list(row.get("unresolved_claims") or []),
            )
        )
    if isinstance(provider, DryRunProvider):
        return _fill_opportunities(cards, brief, evidence, count)[:count]
    if len(cards) < count:
        raise RuntimeError(
            f"opportunity discovery returned {len(cards)} valid rows; required {count}; no filler was generated"
        )
    return cards[:count]


def mine_mechanisms(provider: LLMProvider, brief: CompetitionBrief, count: int) -> list[MechanismCard]:
    template, _ = load_prompt("mechanism-mining")
    rows: list[Any] = []
    batch_size = count if isinstance(provider, DryRunProvider) else 4
    constraints = {
        "mandatory_technologies": brief.mandatory_technologies(),
        "structured_requirements": [
            requirement.model_dump() for requirement in brief.requirements if requirement.required
        ],
    }
    for start in range(0, count, batch_size):
        batch_count = min(batch_size, count - start)
        schema = _array_wrapper_schema("mechanisms", _mechanism_schema(), count=batch_count)
        try:
            raw = provider.complete_json(
                template,
                str(
                    {
                        "count": batch_count,
                        "batch": {"start": start, "total": count},
                        "competition_constraints": constraints,
                    }
                ),
                schema=schema,
            )
            value = raw.get("mechanisms") if isinstance(raw, dict) else None
            rows.extend(value if isinstance(value, list) else [])
        except Exception:
            if not isinstance(provider, DryRunProvider):
                raise

    cards: list[MechanismCard] = []
    for index, row in enumerate(rows or []):
        if not isinstance(row, dict) or _looks_like_product(row):
            if not isinstance(provider, DryRunProvider):
                raise RuntimeError(
                    f"mechanism mining returned an invalid product-shaped row at index {index}"
                )
            continue
        cards.append(
            MechanismCard(
                id=str(row.get("id") or f"mech-{index + 1:02d}"),
                mechanism_family=str(row.get("mechanism_family") or "transformation"),
                mechanism=str(row.get("mechanism") or ""),
                origin_domain=str(row.get("origin_domain") or "systems engineering"),
                inputs=list(row.get("inputs") or []),
                transformation=str(row.get("transformation") or ""),
                outputs=list(row.get("outputs") or []),
                constraints=list(row.get("constraints") or []),
            )
        )
    if isinstance(provider, DryRunProvider):
        return _fill_mechanisms(cards, count)[:count]
    if len(cards) < count:
        raise RuntimeError(
            f"mechanism mining returned {len(cards)} valid rows; required {count}; no filler was generated"
        )
    return cards[:count]


def cross_concepts(
    provider: LLMProvider,
    brief: CompetitionBrief,
    opportunities: list[OpportunityCard],
    mechanisms: list[MechanismCard],
    count: int,
    evidence: list[EvidenceSource] | None = None,
    winner_patterns: dict[str, Any] | None = None,
) -> tuple[list[CandidateIdea], list[IdeaLineage]]:
    if not opportunities or not mechanisms:
        raise ValueError("cross_concepts requires opportunities and mechanisms")
    template, _ = load_prompt("idea-crossing")
    verified = [source for source in (evidence or []) if source.fetch_status == "ok" and source.verified]
    rows: list[Any] = []
    batch_size = count if isinstance(provider, DryRunProvider) else 2
    for start in range(0, count, batch_size):
        batch_count = min(batch_size, count - start)
        schema = _array_wrapper_schema(
            "concepts",
            _candidate_schema(brief),
            count=batch_count,
        )
        payload = {
            "count": batch_count,
            "batch": {"start": start, "total": count},
            "lanes": ["institutional", "systems", "edge-users", "incentives", "physical", "research"],
            "brief": brief.model_dump(),
            "opportunities": [
                opportunities[(start + index) % len(opportunities)].model_dump()
                for index in range(batch_count)
            ],
            "mechanisms": [
                mechanisms[(start + index) % len(mechanisms)].model_dump()
                for index in range(batch_count)
            ],
            "verified_evidence_catalog": [
                {"id": source.id, "url": source.url, "title": source.title} for source in verified
            ],
            "crowding_is_negative_evidence": brief.crowding.model_dump(),
        }
        if winner_patterns:
            payload["winner_patterns"] = winner_patterns
        try:
            raw = provider.complete_json(template, str(payload), schema=schema)
            value = raw.get("concepts") if isinstance(raw, dict) else None
            rows.extend(value if isinstance(value, list) else [])
        except Exception:
            if not isinstance(provider, DryRunProvider):
                raise

    if not rows and isinstance(provider, DryRunProvider):
        fixture_rows = provider.fixture_bundle.get("ideation")
        rows = fixture_rows if isinstance(fixture_rows, list) else []
    if not isinstance(provider, DryRunProvider) and len(rows) < count:
        raise RuntimeError(
            f"idea crossing returned {len(rows)} concepts; required {count}; no synthetic concepts were generated"
        )

    ideas: list[CandidateIdea] = []
    lineage: list[IdeaLineage] = []
    for index in range(count):
        row = dict(rows[index % len(rows)]) if rows else {}
        opportunity = opportunities[index % len(opportunities)]
        mechanism = mechanisms[(index * 5 + index // 4) % len(mechanisms)]
        if isinstance(provider, DryRunProvider) and row:
            row.update(
                {
                    "primary_user": opportunity.user_class,
                    "painful_workflow": opportunity.painful_workflow,
                    "track_fit": opportunity.track,
                    "evidence_ids": opportunity.evidence_ids,
                    "opportunity_id": opportunity.id,
                    "mechanism_id": mechanism.id,
                }
            )
        source = verified[index % len(verified)] if verified else None
        idea = _normalize_concept(row, index, brief, opportunity, mechanism, source=source)
        if any(existing.id == idea.id for existing in ideas):
            idea.id = f"{idea.id}-{index + 1}"
        ideas.append(idea)
        lineage.append(
            IdeaLineage(
                idea_id=idea.id,
                opportunity_id=opportunity.id,
                mechanism_id=mechanism.id,
            )
        )
    return ideas, lineage


def mutate_concepts(
    provider: LLMProvider,
    brief: CompetitionBrief,
    parents: list[CandidateIdea],
    opportunities: list[OpportunityCard],
    mechanisms: list[MechanismCard],
    *,
    round_number: int,
    count: int,
    targets: list[str],
    evidence: list[EvidenceSource] | None = None,
) -> tuple[list[CandidateIdea], list[IdeaLineage]]:
    if not parents or not opportunities or not mechanisms:
        raise ValueError("mutate_concepts requires parents, opportunities, and mechanisms")
    template, _ = load_prompt("reflective-mutation")
    verified = [source for source in (evidence or []) if source.fetch_status == "ok" and source.verified]
    rows: list[Any] = []
    batch_size = count if isinstance(provider, DryRunProvider) else 2
    for start in range(0, count, batch_size):
        batch_count = min(batch_size, count - start)
        schema = _array_wrapper_schema("mutations", _candidate_schema(brief), count=batch_count)
        payload = {
            "count": batch_count,
            "batch": {"start": start, "total": count},
            "round": round_number,
            "empty_or_failed_regions": targets[start : start + batch_count],
            "parents": [
                parents[(start + index) % len(parents)].model_dump()
                for index in range(min(max(2, batch_count), len(parents)))
            ],
            "opportunities": [
                opportunities[(start + index) % len(opportunities)].model_dump()
                for index in range(batch_count)
            ],
            "mechanisms": [
                mechanisms[(start + index) % len(mechanisms)].model_dump()
                for index in range(batch_count)
            ],
            "brief": brief.model_dump(),
            "verified_evidence_catalog": [
                {"id": source.id, "url": source.url, "title": source.title} for source in verified
            ],
        }
        try:
            raw = provider.complete_json(template, str(payload), schema=schema)
            value = raw.get("mutations") if isinstance(raw, dict) else None
            rows.extend(value if isinstance(value, list) else [])
        except Exception:
            if not isinstance(provider, DryRunProvider):
                raise

    if not isinstance(provider, DryRunProvider) and len(rows) < count:
        raise RuntimeError(
            f"reflective mutation returned {len(rows)} concepts; required {count}; no synthetic mutations were generated"
        )

    ideas: list[CandidateIdea] = []
    lineage: list[IdeaLineage] = []
    for index in range(count):
        parent = parents[index % len(parents)]
        opportunity = opportunities[(index + round_number * 7) % len(opportunities)]
        mechanism = mechanisms[(index * 7 + round_number * 3) % len(mechanisms)]
        row = dict(rows[index % len(rows)]) if rows else {}
        source = verified[index % len(verified)] if verified else None
        idea = _normalize_concept(
            row,
            index + round_number * 100,
            brief,
            opportunity,
            mechanism,
            source=source,
        )
        idea.id = f"mut-r{round_number}-{index + 1:02d}-{slugify(idea.working_title)[:28]}"
        idea.mutation_history = list(parent.mutation_history) + [
            f"round {round_number}: {targets[index % len(targets)] if targets else 'structural divergence'}"
        ]
        if not rows and isinstance(provider, DryRunProvider):
            idea.primary_user = opportunity.user_class
            idea.painful_workflow = opportunity.painful_workflow
            idea.imported_mechanism = mechanism.mechanism
            idea.mechanism_origin = mechanism.origin_domain
            idea.mechanism_family = mechanism.mechanism_family
            idea.last_mile_action = _mutation_actions()[(index + round_number) % len(_mutation_actions())]
            idea.demo_type = _proof_types()[(index * 2 + round_number) % len(_proof_types())]
            idea.killer_demo = (
                f"Produce competition-relevant proof by {idea.last_mile_action}; "
                f"validate it using {idea.demo_type}"
            )
            idea.demo_proof = idea.killer_demo
        ideas.append(idea)
        lineage.append(
            IdeaLineage(
                idea_id=idea.id,
                parent_ids=[parent.id],
                opportunity_id=opportunity.id,
                mechanism_id=mechanism.id,
                mutation_round=round_number,
                mutation_target=targets[index % len(targets)] if targets else "structural divergence",
                mutation_notes="Changed at least two structural dimensions.",
            )
        )
    return ideas, lineage


class SparseIdeaArchive:
    """Small native MAP-Elites-style archive keyed by behavior dimensions."""

    dimensions = (
        "track",
        "user_class",
        "workflow",
        "mechanism_family",
        "data",
        "last_mile_action",
        "demo_type",
    )

    def __init__(self) -> None:
        self.cells: dict[tuple[str, ...], CandidateIdea] = {}
        self.quality: dict[tuple[str, ...], float] = {}
        self.replaced: list[dict[str, Any]] = []

    def insert(self, idea: CandidateIdea) -> bool:
        key = self.cell_key(idea)
        score = external_quality(idea)
        previous = self.cells.get(key)
        if previous is None or score > self.quality[key]:
            if previous is not None:
                self.replaced.append(
                    {
                        "cell": list(key),
                        "killed_id": previous.id,
                        "replacement_id": idea.id,
                        "reason": "higher external quality",
                    }
                )
            self.cells[key] = idea
            self.quality[key] = score
            return True
        self.replaced.append(
            {
                "cell": list(key),
                "killed_id": idea.id,
                "replacement_id": previous.id,
                "reason": "occupied by stronger elite",
            }
        )
        return False

    def cell_key(self, idea: CandidateIdea) -> tuple[str, ...]:
        vector = novelty_vector(idea)
        idea.novelty_vector = vector
        return tuple(_bucket(getattr(vector, dimension)) for dimension in self.dimensions)

    def elites(self) -> list[CandidateIdea]:
        return sorted(self.cells.values(), key=external_quality, reverse=True)

    def empty_region_targets(self, limit: int = 8) -> list[str]:
        represented = [
            {dimension: key[index] for index, dimension in enumerate(self.dimensions)}
            for key in self.cells
        ]
        targets: list[str] = []
        for action in _mutation_actions():
            if not any(_bucket(action) == row["last_mile_action"] for row in represented):
                targets.append(f"empty action region: {action}")
        for proof in _proof_types():
            if not any(_bucket(proof) == row["demo_type"] for row in represented):
                targets.append(f"empty proof region: {proof}")
        if not targets:
            targets = ["increase minimum structural distance", "repair collision without cosmetic renaming"]
        return (targets * (limit // len(targets) + 1))[:limit]

    def export(self) -> dict[str, Any]:
        return {
            "dimensions": list(self.dimensions),
            "occupied_cells": len(self.cells),
            "cells": [
                {"cell": list(key), "quality": self.quality[key], "idea": idea.model_dump()}
                for key, idea in self.cells.items()
            ],
            "replacements_and_kills": self.replaced,
        }


def novelty_vector(idea: CandidateIdea) -> NoveltyVector:
    return NoveltyVector(
        track=idea.track_fit,
        user_class=idea.primary_user,
        workflow=idea.painful_workflow,
        mechanism_family=idea.mechanism_family or idea.imported_mechanism,
        data=" | ".join(idea.data_sources),
        last_mile_action=idea.last_mile_action,
        demo_type=idea.demo_type or _infer_proof_type(idea.killer_demo),
    )


def structural_distance(a: CandidateIdea, b: CandidateIdea) -> float:
    left = novelty_vector(a)
    right = novelty_vector(b)
    weights = {
        "track": 0.05,
        "user_class": 0.18,
        "workflow": 0.19,
        "mechanism_family": 0.19,
        "data": 0.08,
        "last_mile_action": 0.17,
        "demo_type": 0.14,
    }
    return sum(
        weights[key] * _text_distance(getattr(left, key), getattr(right, key)) for key in weights
    )


def mmr_select(
    ideas: list[CandidateIdea],
    limit: int,
    *,
    minimum_distance: float = 0.28,
    diversity_weight: float = 0.45,
) -> list[CandidateIdea]:
    pool = list({idea.id: idea for idea in ideas}.values())
    if not pool or limit <= 0:
        return []
    embedded_distances = _dimension_embedding_distances(pool)

    def distance(left: CandidateIdea, right: CandidateIdea) -> float:
        key = (left.id, right.id) if left.id <= right.id else (right.id, left.id)
        return embedded_distances.get(key, structural_distance(left, right))

    selected = [max(pool, key=external_quality)]
    pool.remove(selected[0])
    while pool and len(selected) < limit:
        ranked = sorted(
            pool,
            key=lambda idea: (
                (1 - diversity_weight) * external_quality(idea)
                + diversity_weight * min(distance(idea, chosen) for chosen in selected)
            ),
            reverse=True,
        )
        pick = next(
            (
                idea
                for idea in ranked
                if min(distance(idea, chosen) for chosen in selected) >= minimum_distance
            ),
            ranked[0],
        )
        selected.append(pick)
        pool.remove(pick)
    return selected


def external_quality(idea: CandidateIdea) -> float:
    """Competition-neutral structural quality before official judging."""
    evidence = min(1.0, len(set(idea.evidence_ids)) / 2) if idea.evidence_ids else 0.35
    feasibility = 1.0 if idea.minimum_demonstrable_loop else 0.35
    core_depth = min(1.0, len(_tokens(idea.core_computation)) / 16)
    actionability = 1.0 if idea.last_mile_action.strip() else 0.2
    differentiation = 1.0 if idea.hard_to_fake_advantage.strip() else 0.35
    scores = {
        "evidence_quality": evidence,
        "feasibility": feasibility,
        "core_depth": core_depth,
        "actionability": actionability,
        "differentiation": differentiation,
    }
    idea.external_evaluation_scores = scores
    return sum(scores.values()) / len(scores)


def _dimension_embedding_distances(ideas: list[CandidateIdea]) -> dict[tuple[str, str], float]:
    if len(ideas) < 2 or not env_flag("HACKFORGE_USE_SENTENCE_TRANSFORMERS", default=True):
        return {}
    try:
        import numpy as np

        from hackforge.collision.embed_index import EmbedIndex

        dimensions = list(SparseIdeaArchive.dimensions)
        texts: list[str] = []
        for idea in ideas:
            vector = novelty_vector(idea)
            texts.extend(f"{dimension}: {getattr(vector, dimension)}" for dimension in dimensions)
        matrix = EmbedIndex().encode(texts).reshape(len(ideas), len(dimensions), -1)
        weights = np.asarray([0.05, 0.18, 0.19, 0.19, 0.08, 0.17, 0.14], dtype=np.float32)
        output: dict[tuple[str, str], float] = {}
        per_idea: dict[str, dict[str, float]] = {idea.id: {} for idea in ideas}
        for left_index, left in enumerate(ideas):
            for right_index in range(left_index + 1, len(ideas)):
                right = ideas[right_index]
                per_dimension = 1.0 - np.sum(matrix[left_index] * matrix[right_index], axis=1)
                value = float(np.clip(np.sum(per_dimension * weights), 0.0, 1.0))
                key = (left.id, right.id) if left.id <= right.id else (right.id, left.id)
                output[key] = value
                for dim_index, dimension in enumerate(dimensions):
                    per_idea[left.id].setdefault(dimension, 0.0)
                    per_idea[right.id].setdefault(dimension, 0.0)
                    per_idea[left.id][dimension] += float(per_dimension[dim_index])
                    per_idea[right.id][dimension] += float(per_dimension[dim_index])
        denominator = max(1, len(ideas) - 1)
        for idea in ideas:
            vector = novelty_vector(idea)
            vector.embedding_distances = {
                dimension: value / denominator for dimension, value in per_idea[idea.id].items()
            }
            idea.novelty_vector = vector
        return output
    except Exception as exc:
        raise RuntimeError(
            "Semantic idea-distance calculation failed; no lexical fallback was used. "
            "Install/cache the configured sentence-transformer model or explicitly set "
            "HACKFORGE_USE_SENTENCE_TRANSFORMERS=0 for fixture-only tests."
        ) from exc


def _normalize_concept(
    row: dict[str, Any],
    index: int,
    brief: CompetitionBrief,
    opportunity: OpportunityCard,
    mechanism: MechanismCard,
    *,
    source: EvidenceSource | None = None,
) -> CandidateIdea:
    title = str(
        row.get("working_title")
        or row.get("title")
        or f"{mechanism.mechanism_family} for {opportunity.user_class}"
    )
    evidence_ids = list(row.get("evidence_ids") or opportunity.evidence_ids or ([source.id] if source else []))
    track = str(
        row.get("track_fit")
        or opportunity.track
        or (brief.tracks[index % len(brief.tracks)] if brief.tracks else "")
    )
    data_sources = list(row.get("data_sources") or [])
    data_required = bool(brief.data_requirements) or any(
        requirement.required and requirement.category == "data" for requirement in brief.requirements
    )
    if data_required and not data_sources and brief.available_datasets:
        data_sources = [brief.available_datasets[0]]

    action = str(row.get("last_mile_action") or _mutation_actions()[index % len(_mutation_actions())])
    proof_type = str(row.get("demo_type") or _proof_types()[index % len(_proof_types())])
    proof = str(
        row.get("killer_demo")
        or f"Produce judge-legible proof of the result after the core mechanism and {action}"
    )
    core = str(row.get("core_computation") or mechanism.transformation)

    idea = CandidateIdea(
        id=str(row.get("id") or f"idea-{index + 1:02d}-{slugify(title)[:32]}"),
        lane=str(row.get("lane") or ("institutional", "systems", "edge-users", "incentives", "physical", "research")[index % 6]),
        disciplines=list(row.get("disciplines") or [mechanism.origin_domain]),
        working_title=title,
        primary_user=str(row.get("primary_user") or opportunity.user_class),
        painful_workflow=str(row.get("painful_workflow") or opportunity.painful_workflow),
        current_workaround=str(row.get("current_workaround") or "manual or existing process"),
        imported_mechanism=str(row.get("imported_mechanism") or mechanism.mechanism),
        mechanism_origin=str(row.get("mechanism_origin") or mechanism.origin_domain),
        mechanism_family=str(row.get("mechanism_family") or mechanism.mechanism_family),
        data_sources=data_sources,
        core_computation=core,
        last_mile_action=action,
        visible_transformation=str(
            row.get("visible_transformation") or f"Initial state becomes a validated {action} result"
        ),
        sponsor_dependency=str(row.get("sponsor_dependency") or ""),
        technical_risk=str(row.get("technical_risk") or "execution and validation risk"),
        collision_risk="unknown",
        why_now=str(row.get("why_now") or opportunity.why_now),
        kill_reason=str(row.get("kill_reason") or ""),
        killer_demo=proof,
        hard_to_fake_advantage=str(
            row.get("hard_to_fake_advantage") or "reproducible competition-relevant proof"
        ),
        evidence_ids=evidence_ids,
        opportunity_id=str(row.get("opportunity_id") or opportunity.id),
        mechanism_id=str(row.get("mechanism_id") or mechanism.id),
        track_fit=track,
        technology_roles=_coerce_string_map(row.get("technology_roles")),
        requirement_satisfaction=_coerce_string_map(row.get("requirement_satisfaction")),
        data_access_status=_normalize_data_access_status(
            str(row.get("data_access_status") or _default_data_status(data_sources, brief)),
            data_sources=data_sources,
            plan=str(row.get("data_access_plan") or _default_data_plan(data_sources, brief)),
        ),
        data_access_plan=str(row.get("data_access_plan") or _default_data_plan(data_sources, brief)),
        testable_claim=str(row.get("testable_claim") or ""),
        demo_proof=str(row.get("demo_proof") or proof),
        minimum_demonstrable_loop=str(
            row.get("minimum_demonstrable_loop") or _delivery_plan(brief, core, action)
        ),
        demo_type=proof_type,
    )
    _apply_requirement_defaults(idea, brief)
    return idea


def _normalize_data_access_status(status: str, *, data_sources: list[str], plan: str) -> str:
    """Map free-form LLM prose onto the closed status vocabulary used by data gates."""
    allowed = {
        "verified",
        "available",
        "provided",
        "local",
        "fixture",
        "generated_fixture",
        "synthetic_fixture",
        "sensor",
        "user_supplied",
        "not_required",
        "unverified",
        "not_applicable",
    }
    text = status.strip().lower()
    if text in allowed:
        return text
    # Exact first token / enum-like prefix.
    first = re.split(r"[\s:;,.]+", text, maxsplit=1)[0]
    if first in allowed:
        return first
    blob = f"{text}\n{plan}\n{' '.join(data_sources)}".lower()
    if any(token in blob for token in ("synthetic fixture", "generated fixture", "generated_fixture", "synthetic_fixture")):
        return "generated_fixture"
    if "fixture" in blob or "datapack" in blob or "sample data" in blob or "quickstart" in blob:
        return "fixture"
    if any(token in blob for token in ("user-supplied", "user supplied", "entrant-owned", "entrant owned", "team-provided", "team provided")):
        return "user_supplied"
    if "local" in blob or "repository" in blob or "seed local" in blob:
        return "local"
    if "provided" in blob or "competition resource" in blob or "official resource" in blob:
        return "provided"
    if "available" in blob or "permitted" in blob or "viable" in blob or "credible" in blob:
        return "available"
    if not data_sources:
        return "not_required"
    return "unverified"


def _coerce_string_map(value: Any) -> dict[str, str]:
    """Accept dict maps or Codex-safe [{key,value}] arrays."""
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items() if str(key).strip() and str(item).strip()}
    if isinstance(value, list):
        output: dict[str, str] = {}
        for row in value:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key") or row.get("name") or row.get("technology") or row.get("requirement") or "").strip()
            item = str(row.get("value") or row.get("role") or row.get("explanation") or "").strip()
            if key and item:
                output[key] = item
        return output
    return {}


def _apply_requirement_defaults(idea: CandidateIdea, brief: CompetitionBrief) -> None:
    for technology in brief.mandatory_technologies():
        if not _technology_role(idea, technology):
            idea.technology_roles[technology] = (
                f"{technology} is materially used in the core path: {idea.core_computation}. "
                "Removing it must materially change or break the required implementation."
            )

    for requirement in brief.requirements:
        if not requirement.required or requirement.category == "eligibility":
            continue
        if requirement.category in {"technology", "platform"}:
            explanation = _technology_role(idea, requirement.description) or (
                f"Implement {requirement.description} materially and verify it during feasibility review."
            )
        elif requirement.category == "data":
            explanation = idea.data_access_plan or ", ".join(idea.data_sources)
        elif requirement.category == "demo":
            explanation = idea.demo_proof or idea.killer_demo
        elif requirement.category == "track":
            explanation = idea.track_fit
        elif requirement.category in {"timebox", "team"}:
            explanation = idea.minimum_demonstrable_loop
        elif requirement.category == "sponsor":
            explanation = idea.sponsor_dependency or f"Satisfy sponsor requirement: {requirement.description}"
        else:
            explanation = f"Plan and verify required condition: {requirement.description}"
        if explanation:
            idea.requirement_satisfaction.setdefault(requirement.id, explanation)

    for artifact in brief.submission_artifacts:
        idea.requirement_satisfaction.setdefault(
            f"artifact:{artifact}",
            f"Produce and validate required submission artifact: {artifact}",
        )


def _default_data_status(data_sources: list[str], brief: CompetitionBrief) -> str:
    if not data_sources:
        return "not_required"
    if all(source in brief.available_datasets for source in data_sources):
        return "provided"
    return "unverified"


def _default_data_plan(data_sources: list[str], brief: CompetitionBrief) -> str:
    if not data_sources:
        return ""
    if all(source in brief.available_datasets for source in data_sources):
        return "Use the competition-provided/explicitly available data and verify access before implementation."
    return "Verify access, permission, format, and reproducibility for every named data source before build commitment."


def _delivery_plan(brief: CompetitionBrief, core: str, action: str) -> str:
    constraint = brief.build_window or (f"before the deadline {brief.deadline}" if brief.deadline else "")
    team = f" with team constraint {brief.team_size}" if brief.team_size else ""
    if constraint:
        return (
            f"Within {constraint}{team}, prepare required inputs/resources, implement the core ({core}), "
            f"produce the result ({action}), validate mandatory requirements, and prepare submission artifacts."
        )
    return (
        f"Prepare required inputs/resources, implement the core ({core}), produce the result ({action}), "
        "validate mandatory requirements, and prepare the smallest complete submission without inventing a timebox."
    )


def _technology_role(idea: CandidateIdea, technology: str) -> str:
    wanted = _norm(technology)
    for key, role in idea.technology_roles.items():
        current = _norm(key)
        if current == wanted or current in wanted or wanted in current:
            return role
    return ""


def _fill_opportunities(
    existing: list[OpportunityCard],
    brief: CompetitionBrief,
    evidence: list[EvidenceSource],
    count: int,
) -> list[OpportunityCard]:
    cards = list(existing)
    source_ids = [source.id for source in evidence if source.fetch_status == "ok"]
    users = [
        "people handling exception-heavy decisions",
        "small teams reviewing inconsistent evidence",
        "operators transferring cases between systems",
        "participants validating uncertain results",
        "engineers reproducing intermittent failures",
        "field teams coordinating time-sensitive actions",
        "independent workers documenting commitments",
        "communities validating local claims",
    ]
    workflows = [
        "reconstructing which rule and evidence applied at a past decision",
        "detecting conflicts before a handoff causes rework",
        "turning ambiguous requirements into auditable acceptance tests",
        "comparing an attempted solution with the actual failure gap",
        "replaying failures across changing tools and data",
        "prioritizing actions under incomplete and contradictory evidence",
        "proving what changed between a promise and delivered work",
        "separating sourced facts from repeated assumptions",
    ]
    while len(cards) < count:
        index = len(cards)
        user = users[index % len(users)]
        workflow = workflows[(index * 3 + index // len(users)) % len(workflows)]
        cards.append(
            OpportunityCard(
                id=f"opp-{index + 1:02d}",
                user_class=user,
                painful_workflow=workflow,
                unmet_need="A fast, inspectable way to complete the objective without hiding uncertainty",
                evidence_ids=source_ids[index % len(source_ids) : index % len(source_ids) + 1] if source_ids else [],
                track=brief.tracks[index % len(brief.tracks)] if brief.tracks else "",
                why_now="Current tools make the underlying transformation practical to validate",
                unresolved_claims=[] if source_ids else ["No retrievable source was available for this opportunity"],
            )
        )
    return cards


def _fill_mechanisms(existing: list[MechanismCard], count: int) -> list[MechanismCard]:
    cards = list(existing)
    library = [
        ("temporal verification", "bitemporal rule diffing", "database reliability", "Compare state at event-time and knowledge-time"),
        ("constraint solving", "minimal unsatisfied constraint extraction", "operations research", "Find the smallest blocking constraint set"),
        ("counterfactual", "counterfactual intervention testing", "causal inference", "Vary one actionable input and measure outcome change"),
        ("provenance", "claim-evidence dependency graphs", "scientific reproducibility", "Trace conclusions to supporting/conflicting evidence"),
        ("simulation", "discrete-event workflow simulation", "industrial engineering", "Replay queues and interventions under fixed scenarios"),
        ("anomaly detection", "invariant violation detection", "reliability engineering", "Surface transitions that violate expected invariants"),
        ("optimization", "robust multi-objective optimization", "operations research", "Optimize actions across uncertain objectives and constraints"),
        ("testing", "metamorphic test generation", "verification", "Generate transformations whose output relation must hold"),
        ("control", "feedback control with guardrails", "control theory", "Measure deviation and choose a bounded corrective action"),
        ("matching", "stable matching with explainable constraints", "market design", "Allocate participants/resources without unstable blocking pairs"),
        ("compression", "minimum-description exception summaries", "information theory", "Compress a case while retaining decision-changing exceptions"),
        ("adversarial audit", "red-team claim mutation", "security engineering", "Mutate claims until unsupported reasoning fails visibly"),
    ]
    while len(cards) < count:
        index = len(cards)
        family, mechanism, origin, transformation = library[index % len(library)]
        cycle = index // len(library)
        cards.append(
            MechanismCard(
                id=f"mech-{index + 1:02d}",
                mechanism_family=family,
                mechanism=mechanism if not cycle else f"{mechanism} under uncertainty",
                origin_domain=origin,
                inputs=["observations/resources", "constraints", "provenance"],
                transformation=transformation,
                outputs=["verifiable result", "human-inspectable explanation or artifact"],
                constraints=["bounded execution", "preserve uncertainty", "no target-format assumptions"],
            )
        )
    return cards


def _looks_like_product(row: dict[str, Any]) -> bool:
    forbidden_fields = {"working_title", "features", "primary_user", "killer_demo", "last_mile_action", "product"}
    return len(forbidden_fields.intersection(row)) >= 2


def _infer_proof_type(text: str) -> str:
    blob = text.lower()
    if "prototype" in blob or "physical" in blob:
        return "prototype"
    if "benchmark" in blob or "accuracy" in blob or "score" in blob:
        return "benchmark"
    if "presentation" in blob or "pitch" in blob:
        return "presentation"
    if "replay" in blob:
        return "replay"
    if "before" in blob and "after" in blob:
        return "before-after"
    return "artifact-proof"


def _mutation_actions() -> list[str]:
    return [
        "write a verified correction into the workflow",
        "schedule the next bounded action",
        "block an unsafe transition with evidence",
        "run a reproducible validation test",
        "reallocate a constrained resource",
        "open a review task containing the minimal conflict set",
        "update a provenance record",
        "trigger a counterfactual comparison",
        "produce a validated physical prototype",
        "submit a scored model or analysis result",
        "present an evidence-backed decision or pitch",
    ]


def _proof_types() -> list[str]:
    return [
        "before-after",
        "replay",
        "benchmark",
        "failure injection",
        "counterfactual",
        "state transition",
        "physical prototype",
        "presentation",
        "artifact review",
        "measured outcome",
    ]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "for",
        "in",
        "with",
    }


def _text_distance(left: str, right: str) -> float:
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens and not right_tokens:
        return 0.0
    return 1.0 - len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))


def _bucket(text: str) -> str:
    tokens = sorted(_tokens(text))[:3]
    return "-".join(tokens) if tokens else "unspecified"


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _array_wrapper_schema(key: str, item_schema: dict[str, Any], *, count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            key: {
                "type": "array",
                "items": item_schema,
                "minItems": count,
                "maxItems": count,
            }
        },
        "required": [key],
        "additionalProperties": False,
    }


def _opportunity_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "user_class": {"type": "string"},
            "painful_workflow": {"type": "string"},
            "unmet_need": {"type": "string"},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
            "track": {"type": "string"},
            "why_now": {"type": "string"},
            "unresolved_claims": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "user_class", "painful_workflow", "unmet_need", "evidence_ids"],
        "additionalProperties": False,
    }


def _mechanism_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "mechanism_family": {"type": "string"},
            "mechanism": {"type": "string"},
            "origin_domain": {"type": "string"},
            "inputs": {"type": "array", "items": {"type": "string"}},
            "transformation": {"type": "string"},
            "outputs": {"type": "array", "items": {"type": "string"}},
            "constraints": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "mechanism_family", "mechanism", "origin_domain", "transformation"],
        "additionalProperties": False,
    }


def _candidate_schema(brief: CompetitionBrief) -> dict[str, Any]:
    required_strings = [
        "id",
        "lane",
        "working_title",
        "primary_user",
        "painful_workflow",
        "current_workaround",
        "imported_mechanism",
        "core_computation",
        "last_mile_action",
        "visible_transformation",
        "killer_demo",
        "hard_to_fake_advantage",
    ]
    properties: dict[str, Any] = {
        field: {"type": "string", "minLength": 1} for field in required_strings
    }
    properties.update(
        {
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
            "data_sources": {"type": "array", "items": {"type": "string"}},
            "data_access_status": {
                "type": "string",
                "enum": [
                    "verified",
                    "available",
                    "provided",
                    "local",
                    "fixture",
                    "generated_fixture",
                    "synthetic_fixture",
                    "sensor",
                    "user_supplied",
                    "not_required",
                    "unverified",
                ],
            },
            "data_access_plan": {"type": "string"},
            "track_fit": {"type": "string"},
            "sponsor_dependency": {"type": "string"},
            "technical_risk": {"type": "string"},
            "technology_roles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "minLength": 1},
                        "value": {"type": "string", "minLength": 1},
                    },
                    "required": ["key", "value"],
                    "additionalProperties": False,
                },
            },
            "requirement_satisfaction": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "minLength": 1},
                        "value": {"type": "string", "minLength": 1},
                    },
                    "required": ["key", "value"],
                    "additionalProperties": False,
                },
            },
            "minimum_demonstrable_loop": {"type": "string"},
            "demo_proof": {"type": "string"},
            "demo_type": {"type": "string"},
            "testable_claim": {"type": "string"},
        }
    )
    required = list(required_strings)
    if brief.mandatory_technologies():
        required.append("technology_roles")
    if any(requirement.required and requirement.category != "eligibility" for requirement in brief.requirements) or brief.submission_artifacts:
        required.append("requirement_satisfaction")
    if brief.data_requirements or any(
        requirement.required and requirement.category == "data" for requirement in brief.requirements
    ):
        required.extend(["data_sources", "data_access_status", "data_access_plan"])
    if brief.build_window or brief.deadline or brief.team_size:
        required.append("minimum_demonstrable_loop")
    if brief.demo_requirements or any(
        requirement.required and requirement.category == "demo" for requirement in brief.requirements
    ):
        required.append("demo_proof")
    return {
        "type": "object",
        "properties": properties,
        "required": list(dict.fromkeys(required)),
        "additionalProperties": False,
    }
