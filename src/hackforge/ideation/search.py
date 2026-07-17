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
    # A personal iteration pass: enough structural variety to return a winner
    # plus two different backups without turning an initial brief into a long
    # multi-agent research job. Use balanced for the fuller 48-concept search.
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
                {"id": s.id, "title": s.title, "url": s.url, "excerpt": s.excerpt[:1800]}
                for s in evidence
                if s.fetch_status == "ok"
            ],
        }
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
                raise RuntimeError(f"opportunity discovery returned an invalid product-shaped row at index {index}")
            continue
        try:
            cards.append(
                OpportunityCard(
                    id=str(row.get("id") or f"opp-{index + 1:02d}"),
                    user_class=str(row.get("user_class") or "underserved competition participant"),
                    painful_workflow=str(row.get("painful_workflow") or ""),
                    unmet_need=str(row.get("unmet_need") or ""),
                    evidence_ids=list(row.get("evidence_ids") or []),
                    track=str(row.get("track") or ""),
                    why_now=str(row.get("why_now") or ""),
                    unresolved_claims=list(row.get("unresolved_claims") or []),
                )
            )
        except Exception:
            if not isinstance(provider, DryRunProvider):
                raise
            continue
    if isinstance(provider, DryRunProvider):
        return _fill_opportunities(cards, brief, evidence, count)[:count]
    if len(cards) < count:
        raise RuntimeError(f"opportunity discovery returned {len(cards)} valid rows; required {count}; no filler was generated")
    return cards[:count]


def mine_mechanisms(provider: LLMProvider, brief: CompetitionBrief, count: int) -> list[MechanismCard]:
    template, _ = load_prompt("mechanism-mining")
    rows: list[Any] = []
    batch_size = count if isinstance(provider, DryRunProvider) else 4
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
                        "competition_constraints": brief.required_or_encouraged_tech,
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
                raise RuntimeError(f"mechanism mining returned an invalid product-shaped row at index {index}")
            continue
        try:
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
        except Exception:
            if not isinstance(provider, DryRunProvider):
                raise
            continue
    if isinstance(provider, DryRunProvider):
        return _fill_mechanisms(cards, count)[:count]
    if len(cards) < count:
        raise RuntimeError(f"mechanism mining returned {len(cards)} valid rows; required {count}; no filler was generated")
    return cards[:count]


def cross_concepts(
    provider: LLMProvider,
    brief: CompetitionBrief,
    opportunities: list[OpportunityCard],
    mechanisms: list[MechanismCard],
    count: int,
    evidence: list[EvidenceSource] | None = None,
) -> tuple[list[CandidateIdea], list[IdeaLineage]]:
    template, _ = load_prompt("idea-crossing")
    verified = [source for source in (evidence or []) if source.fetch_status == "ok" and source.verified]
    rows: list[Any] = []
    # Candidate payloads contain strict evidence and gate requirements. Keeping
    # live batches to two avoids long reasoning-only responses that never reach
    # a final JSON value, while still preserving constrained crossings.
    batch_size = count if isinstance(provider, DryRunProvider) else 2
    for start in range(0, count, batch_size):
        batch_count = min(batch_size, count - start)
        schema = _array_wrapper_schema(
            "concepts",
            _candidate_schema(
                brief,
                evidence_ids=[source.id for source in verified],
                data_urls=[source.url for source in verified if source.url.startswith(("http://", "https://"))],
            ),
            count=batch_count,
        )
        payload = {
            "count": batch_count,
            "batch": {"start": start, "total": count},
            "lanes": ["institutional", "systems", "edge-users", "incentives"],
            "brief": brief.model_dump(),
            "opportunities": [
                opportunities[(start + index) % len(opportunities)].model_dump()
                for index in range(min(batch_count, len(opportunities)))
            ],
            "mechanisms": [
                mechanisms[(start + index) % len(mechanisms)].model_dump()
                for index in range(min(batch_count, len(mechanisms)))
            ],
            "verified_evidence_catalog": [
                {"id": source.id, "url": source.url, "title": source.title} for source in verified
            ],
            "data_rule": "Each data_sources URL must come from the verified catalog and its matching id must be in evidence_ids.",
            "crowded_patterns_are_negative_evidence": brief.crowding.model_dump(),
        }
        try:
            raw = provider.complete_json(template, str(payload), schema=schema)
            value = raw.get("concepts") if isinstance(raw, dict) else None
            batch_rows = value if isinstance(value, list) else []
            rows.extend(batch_rows)
        except Exception:
            if not isinstance(provider, DryRunProvider):
                raise
    if not rows and isinstance(provider, DryRunProvider):
        fixture_rows = provider.fixture_bundle.get("ideation")
        rows = fixture_rows if isinstance(fixture_rows, list) else []
    if not isinstance(provider, DryRunProvider) and len(rows) < count:
        raise RuntimeError(f"idea crossing returned {len(rows)} concepts; required {count}; no synthetic concepts were generated")
    ideas: list[CandidateIdea] = []
    lineage: list[IdeaLineage] = []
    for index in range(count):
        row = dict(rows[index % len(rows)]) if rows else {}
        opportunity = opportunities[index % len(opportunities)]
        mechanism = mechanisms[(index * 5 + index // 4) % len(mechanisms)]
        if isinstance(provider, DryRunProvider) and row:
            row.update(
                {
                    "working_title": f"{row.get('working_title') or 'Concept'} — {opportunity.track}",
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
    template, _ = load_prompt("reflective-mutation")
    verified = [source for source in (evidence or []) if source.fetch_status == "ok" and source.verified]
    rows: list[Any] = []
    batch_size = count if isinstance(provider, DryRunProvider) else 2
    for start in range(0, count, batch_size):
        batch_count = min(batch_size, count - start)
        schema = _array_wrapper_schema(
            "mutations",
            _candidate_schema(
                brief,
                evidence_ids=[source.id for source in verified],
                data_urls=[source.url for source in verified if source.url.startswith(("http://", "https://"))],
            ),
            count=batch_count,
        )
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
                for index in range(min(batch_count, len(opportunities)))
            ],
            "mechanisms": [
                mechanisms[(start + index) % len(mechanisms)].model_dump()
                for index in range(min(batch_count, len(mechanisms)))
            ],
            "brief": brief.model_dump(),
            "verified_evidence_catalog": [
                {"id": source.id, "url": source.url, "title": source.title} for source in verified
            ],
            "data_rule": "Each data_sources URL must come from the verified catalog and its matching id must be in evidence_ids.",
        }
        try:
            raw = provider.complete_json(template, str(payload), schema=schema)
            value = raw.get("mutations") if isinstance(raw, dict) else None
            batch_rows = value if isinstance(value, list) else []
            rows.extend(batch_rows)
        except Exception:
            if not isinstance(provider, DryRunProvider):
                raise
    if not isinstance(provider, DryRunProvider) and len(rows) < count:
        raise RuntimeError(f"reflective mutation returned {len(rows)} concepts; required {count}; no synthetic mutations were generated")
    ideas: list[CandidateIdea] = []
    lineage: list[IdeaLineage] = []
    for index in range(count):
        parent = parents[index % len(parents)]
        opportunity = opportunities[(index + round_number * 7) % len(opportunities)]
        mechanism = mechanisms[(index * 7 + round_number * 3) % len(mechanisms)]
        row = rows[index % len(rows)] if rows else {}
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
            idea.demo_type = _demo_types()[(index * 2 + round_number) % len(_demo_types())]
            idea.killer_demo = (
                f"Run a fixed before/after fixture and visibly {idea.last_mile_action}; "
                f"display a measured result using a {idea.demo_type} demo"
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
                mutation_notes="Changed at least user/workflow pairing and mechanism/action/demo pairing.",
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
                    {"cell": list(key), "killed_id": previous.id, "replacement_id": idea.id, "reason": "higher external quality"}
                )
            self.cells[key] = idea
            self.quality[key] = score
            return True
        self.replaced.append(
            {"cell": list(key), "killed_id": idea.id, "replacement_id": previous.id, "reason": "occupied by stronger elite"}
        )
        return False

    def cell_key(self, idea: CandidateIdea) -> tuple[str, ...]:
        vector = novelty_vector(idea)
        idea.novelty_vector = vector
        return tuple(_bucket(getattr(vector, dimension)) for dimension in self.dimensions)

    def elites(self) -> list[CandidateIdea]:
        return sorted(self.cells.values(), key=external_quality, reverse=True)

    def empty_region_targets(self, limit: int = 8) -> list[str]:
        represented = [{dimension: key[i] for i, dimension in enumerate(self.dimensions)} for key in self.cells]
        targets = []
        for action in _mutation_actions():
            if not any(_bucket(action) == row["last_mile_action"] for row in represented):
                targets.append(f"empty action region: {action}")
        for demo in _demo_types():
            if not any(_bucket(demo) == row["demo_type"] for row in represented):
                targets.append(f"empty demo region: {demo}")
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
        demo_type=idea.demo_type or _infer_demo_type(idea.killer_demo),
    )


def structural_distance(a: CandidateIdea, b: CandidateIdea) -> float:
    av = novelty_vector(a)
    bv = novelty_vector(b)
    weights = {
        "track": 0.08,
        "user_class": 0.17,
        "workflow": 0.18,
        "mechanism_family": 0.18,
        "data": 0.10,
        "last_mile_action": 0.16,
        "demo_type": 0.13,
    }
    return sum(weights[key] * _text_distance(getattr(av, key), getattr(bv, key)) for key in weights)


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
        if key in embedded_distances:
            return embedded_distances[key]
        return structural_distance(left, right)

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
            (idea for idea in ranked if min(distance(idea, chosen) for chosen in selected) >= minimum_distance),
            ranked[0],
        )
        selected.append(pick)
        pool.remove(pick)
    return selected


def external_quality(idea: CandidateIdea) -> float:
    """Deterministic evaluator; never consumes proposer-supplied scores."""
    evidence = min(1.0, len(set(idea.evidence_ids)) / 2)
    feasibility = 1.0 if idea.minimum_demonstrable_loop and idea.data_access_status in {"verified", "synthetic_fixture"} else 0.25
    demo = 1.0 if idea.demo_proof and _observable(idea.demo_proof) else 0.2
    technical = min(1.0, len(_tokens(idea.core_computation)) / 16)
    track = 1.0 if idea.track_fit else 0.3
    scores = {
        "evidence_quality": evidence,
        "feasibility": feasibility,
        "demo_proof": demo,
        "technical_depth": technical,
        "track_fit": track,
    }
    idea.external_evaluation_scores = scores
    return sum(scores.values()) / len(scores)


def _dimension_embedding_distances(ideas: list[CandidateIdea]) -> dict[tuple[str, str], float]:
    """Batch Sentence Transformer distances; callers use explicit lexical distance when unavailable."""
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
        weights = np.asarray([0.08, 0.17, 0.18, 0.18, 0.10, 0.16, 0.13], dtype=np.float32)
        output: dict[tuple[str, str], float] = {}
        per_idea: dict[str, dict[str, float]] = {idea.id: {} for idea in ideas}
        for left_index, left in enumerate(ideas):
            for right_index in range(left_index + 1, len(ideas)):
                right = ideas[right_index]
                per_dimension = 1.0 - np.sum(matrix[left_index] * matrix[right_index], axis=1)
                distance = float(np.clip(np.sum(per_dimension * weights), 0.0, 1.0))
                key = (left.id, right.id) if left.id <= right.id else (right.id, left.id)
                output[key] = distance
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
    title = str(row.get("working_title") or row.get("title") or f"{mechanism.mechanism_family} for {opportunity.user_class}")
    evidence_ids = list(row.get("evidence_ids") or ([source.id] if source else opportunity.evidence_ids))
    track = str(row.get("track_fit") or opportunity.track or (brief.tracks[index % len(brief.tracks)] if brief.tracks else "Open"))
    sources = list(row.get("data_sources") or ([source.url] if source else []))
    action = str(row.get("last_mile_action") or _mutation_actions()[index % len(_mutation_actions())])
    demo_type = str(row.get("demo_type") or _demo_types()[index % len(_demo_types())])
    demo = str(
        row.get("killer_demo")
        or f"Load a fixed fixture, show the initial state, run the mechanism, then {action} and display the measured difference"
    )
    return CandidateIdea(
        id=str(row.get("id") or f"idea-{index + 1:02d}-{slugify(title)[:32]}"),
        lane=str(row.get("lane") or ("institutional", "systems", "edge-users", "incentives")[index % 4]),
        disciplines=list(row.get("disciplines") or [mechanism.origin_domain]),
        working_title=title,
        primary_user=str(row.get("primary_user") or opportunity.user_class),
        painful_workflow=str(row.get("painful_workflow") or opportunity.painful_workflow),
        current_workaround=str(row.get("current_workaround") or "manual checking, copying, and ad-hoc judgment"),
        imported_mechanism=str(row.get("imported_mechanism") or mechanism.mechanism),
        mechanism_origin=str(row.get("mechanism_origin") or mechanism.origin_domain),
        mechanism_family=str(row.get("mechanism_family") or mechanism.mechanism_family),
        data_sources=sources,
        core_computation=str(row.get("core_computation") or mechanism.transformation),
        last_mile_action=action,
        visible_transformation=str(row.get("visible_transformation") or f"Unverified workflow state becomes a measurable {action} result"),
        sponsor_dependency=str(row.get("sponsor_dependency") or "GPT-5.6 reasoning and Codex-built evaluation harness"),
        technical_risk=str(row.get("technical_risk") or "quality of the fixed evaluation fixture"),
        collision_risk="unknown",
        why_now=str(row.get("why_now") or opportunity.why_now),
        kill_reason="",
        killer_demo=demo,
        hard_to_fake_advantage=str(row.get("hard_to_fake_advantage") or "reproducible before/after evaluation with cited provenance"),
        evidence_ids=evidence_ids,
        opportunity_id=opportunity.id,
        mechanism_id=mechanism.id,
        track_fit=track,
        gpt_5_6_role=str(
            row.get("gpt_5_6_role")
            or "GPT-5.6 performs the central constrained reasoning transformation and emits evidence-linked structured decisions"
        ),
        codex_build_role=str(
            row.get("codex_build_role")
            or "Codex builds the executable prototype, test fixtures, evaluation harness, and records the required session"
        ),
        data_access_status=str(row.get("data_access_status") or ("verified" if sources else "unverified")),
        data_access_plan=str(
            row.get("data_access_plan")
            or (
                "Fetch the cited public source, cache a fixed fixture, and verify every demo input against it"
                if sources
                else ""
            )
        ),
        testable_claim=str(
            row.get("testable_claim")
            or "The fixed fixture produces a faster or more accurate observable decision than the manual baseline"
        ),
        demo_proof=str(row.get("demo_proof") or demo),
        minimum_demonstrable_loop=str(
            row.get("minimum_demonstrable_loop")
            or "Day 1 fixture and metric; days 2-3 core transformation; day 4 UI/action; day 5 recorded before/after demo"
        ),
        demo_type=demo_type,
    )


def _fill_opportunities(
    existing: list[OpportunityCard],
    brief: CompetitionBrief,
    evidence: list[EvidenceSource],
    count: int,
) -> list[OpportunityCard]:
    cards = list(existing)
    source_ids = [s.id for s in evidence if s.fetch_status == "ok"] or []
    users = [
        "people handling exception-heavy applications",
        "small teams reviewing inconsistent evidence",
        "front-line workers transferring cases between systems",
        "learners who cannot see why an answer failed",
        "developers reproducing intermittent agent failures",
        "caregivers coordinating time-sensitive decisions",
        "independent workers documenting client commitments",
        "community organizers validating local claims",
    ]
    workflows = [
        "reconstructing which rule and evidence applied at a past decision",
        "detecting conflicts before a handoff causes rework",
        "turning ambiguous requests into auditable acceptance tests",
        "comparing an attempted solution with the actual reasoning gap",
        "replaying failures across changing tools and data",
        "prioritizing actions under incomplete and contradictory evidence",
        "proving what changed between a promise and delivered work",
        "separating sourced facts from repeated local assumptions",
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
                unmet_need="A fast, inspectable way to complete the workflow without hiding uncertainty",
                evidence_ids=source_ids[index % len(source_ids) : index % len(source_ids) + 1] if source_ids else [],
                track=brief.tracks[index % len(brief.tracks)] if brief.tracks else "Open",
                why_now="Reasoning models can now produce structured traces that can be automatically checked",
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
        ("provenance", "claim-evidence dependency graphs", "scientific reproducibility", "Trace every conclusion to supporting and conflicting evidence"),
        ("simulation", "discrete-event workflow simulation", "industrial engineering", "Replay queues and interventions under fixed scenarios"),
        ("anomaly detection", "invariant violation detection", "site reliability engineering", "Learn expected invariants and surface violating transitions"),
        ("optimization", "robust multi-objective scheduling", "operations research", "Optimize actions across uncertain objectives and constraints"),
        ("testing", "metamorphic test generation", "software verification", "Generate input transformations whose output relation must hold"),
        ("control", "feedback control with guardrails", "control theory", "Measure deviation and choose a bounded corrective action"),
        ("matching", "stable matching with explainable constraints", "market design", "Allocate participants without unstable blocking pairs"),
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
                inputs=["structured observations", "constraints", "provenance"],
                transformation=transformation,
                outputs=["machine-checkable result", "human-inspectable explanation"],
                constraints=["bounded runtime", "preserve uncertainty", "no target-user assumptions"],
            )
        )
    return cards


def _looks_like_product(row: dict[str, Any]) -> bool:
    forbidden_fields = {"working_title", "features", "primary_user", "killer_demo", "last_mile_action", "product"}
    return len(forbidden_fields.intersection(row)) >= 2


def _observable(text: str) -> bool:
    return any(word in text.lower() for word in ("before", "after", "change", "measure", "display", "show", "emit", "reduce", "compare"))


def _infer_demo_type(text: str) -> str:
    blob = text.lower()
    if "before" in blob and "after" in blob:
        return "before-after"
    if "replay" in blob:
        return "replay"
    if "measure" in blob or "metric" in blob:
        return "benchmark"
    return "state-change"


def _mutation_actions() -> list[str]:
    return [
        "write a verified correction into the workflow",
        "schedule the next bounded action",
        "block an unsafe transition with an evidence receipt",
        "generate and run a regression test",
        "reallocate a constrained resource",
        "open a review task containing the minimal conflict set",
        "update a provenance ledger",
        "trigger a counterfactual comparison",
    ]


def _demo_types() -> list[str]:
    return ["before-after", "live replay", "benchmark", "failure injection", "counterfactual", "state transition"]


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
    a, b = _tokens(left), _tokens(right)
    if not a and not b:
        return 0.0
    return 1.0 - len(a & b) / max(1, len(a | b))


def _bucket(text: str) -> str:
    tokens = sorted(_tokens(text))[:3]
    return "-".join(tokens) if tokens else "unspecified"


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


def _candidate_schema(
    brief: CompetitionBrief,
    *,
    evidence_ids: list[str] | None = None,
    data_urls: list[str] | None = None,
) -> dict[str, Any]:
    # Ask the model only for the product-specific judgement. Provenance, build
    # roles, and the five-day loop are derived from verified evidence by
    # _normalize_concept, preventing huge repetitive JSON arrays from making a
    # live search stall before it reaches the hard gates.
    string_fields = [
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
        "testable_claim",
    ]
    properties: dict[str, Any] = {
        field: {"type": "string", "minLength": 1} for field in string_fields
    }
    properties.update(
        {
            "testable_claim": {
                "type": "string",
                "pattern": "(?i)(than|%|measure|accuracy|time|fewer|more|reduce|increase|baseline)",
            },
        }
    )
    return {
        "type": "object",
        "properties": properties,
        "required": string_fields,
        "additionalProperties": False,
    }
