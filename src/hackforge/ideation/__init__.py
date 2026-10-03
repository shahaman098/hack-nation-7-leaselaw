from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from hackforge.models import CandidateIdea, CompetitionBrief
from hackforge.paths import IDEATION_LANES
from hackforge.providers import LLMProvider
from hackforge.utils import load_prompt, render_prompt, slugify

from .search import SEARCH_PROFILES as SEARCH_PROFILES
from .search import SparseIdeaArchive as SparseIdeaArchive
from .search import cross_concepts as _search_cross_concepts
from .search import discover_opportunities as discover_opportunities
from .search import external_quality as external_quality
from .search import get_search_profile as get_search_profile
from .search import mine_mechanisms as mine_mechanisms
from .search import mmr_select as mmr_select
from .search import mutate_concepts as _search_mutate_concepts
from .search import structural_distance as structural_distance


def cross_concepts(
    provider: LLMProvider,
    brief: CompetitionBrief,
    opportunities: list[Any],
    mechanisms: list[Any],
    count: int,
    evidence: list[Any] | None = None,
    winner_patterns: dict[str, Any] | None = None,
):
    """Public concept crossing with competition-derived defaults."""
    ideas, lineage = _search_cross_concepts(
        provider,
        brief,
        opportunities,
        mechanisms,
        count,
        evidence=evidence,
        winner_patterns=winner_patterns,
    )
    for idea in ideas:
        _apply_competition_requirements(idea, brief)
    return ideas, lineage


def mutate_concepts(
    provider: LLMProvider,
    brief: CompetitionBrief,
    parents: list[CandidateIdea],
    opportunities: list[Any],
    mechanisms: list[Any],
    *,
    round_number: int,
    count: int,
    targets: list[str],
    evidence: list[Any] | None = None,
):
    """Public mutation path with the same generic requirement normalization."""
    ideas, lineage = _search_mutate_concepts(
        provider,
        brief,
        parents,
        opportunities,
        mechanisms,
        round_number=round_number,
        count=count,
        targets=targets,
        evidence=evidence,
    )
    for idea in ideas:
        _apply_competition_requirements(idea, brief)
    return ideas, lineage


def _apply_competition_requirements(idea: CandidateIdea, brief: CompetitionBrief) -> None:
    """Translate the parsed brief into candidate-level implementation obligations."""
    for technology in brief.mandatory_technologies():
        if not _technology_role(idea, technology):
            idea.technology_roles[technology] = (
                f"{technology} is a material dependency in the core path: {idea.core_computation}. "
                "The implementation must materially change or fail if the required technology is removed."
            )

    data_required = bool(brief.data_requirements) or any(
        requirement.required and requirement.category == "data"
        for requirement in brief.requirements
    )
    if not data_required and idea.data_sources and all(
        source in set(brief.source_urls) for source in idea.data_sources
    ):
        # Competition/rules pages are evidence, not automatically product data.
        idea.data_sources = []
        idea.data_access_status = "not_required"
        idea.data_access_plan = ""
    elif data_required and not idea.data_sources and brief.available_datasets:
        idea.data_sources = [brief.available_datasets[0]]
        idea.data_access_status = "provided"
        idea.data_access_plan = (
            "Use the competition-provided or explicitly available dataset and verify access before implementation."
        )

    constraint = brief.build_window or (
        f"the submission deadline {brief.deadline}" if brief.deadline else ""
    )
    team = f" with team constraint {brief.team_size}" if brief.team_size else ""
    if constraint:
        idea.minimum_demonstrable_loop = (
            f"Within {constraint}{team}, implement the smallest complete loop: prepare the required inputs/resources, "
            f"build the core transformation ({idea.core_computation}), produce the result "
            f"({idea.last_mile_action}), then validate the required submission proof."
        )
    else:
        idea.minimum_demonstrable_loop = (
            "Implement the smallest complete loop without inventing a timebox: prepare required inputs/resources, "
            f"build the core transformation ({idea.core_computation}), produce the result "
            f"({idea.last_mile_action}), and validate the competition-relevant output."
        )

    for requirement in brief.requirements:
        if not requirement.required or requirement.category == "eligibility":
            continue
        if requirement.category in {"technology", "platform"}:
            role = _technology_role(idea, requirement.description)
            explanation = role or (
                f"Implement {requirement.description} materially in the core path and verify it during feasibility review."
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
            explanation = idea.sponsor_dependency or (
                f"Satisfy sponsor requirement materially: {requirement.description}"
            )
        else:
            explanation = (
                f"Plan for required condition: {requirement.description}. "
                "Verify the exact submission evidence before finalizing the entry."
            )
        if explanation:
            idea.requirement_satisfaction[requirement.id] = explanation

    for artifact in brief.submission_artifacts:
        idea.requirement_satisfaction[f"artifact:{artifact}"] = (
            f"Produce and validate the required submission artifact: {artifact}."
        )


def _technology_role(idea: CandidateIdea, technology: str) -> str:
    wanted = _norm_text(technology)
    for name, role in idea.technology_roles.items():
        current = _norm_text(name)
        if current == wanted or current in wanted or wanted in current:
            return role
    return ""


def _norm_text(text: str) -> str:
    return " ".join("".join(char.lower() if char.isalnum() else " " for char in text).split())


def run_isolated_ideation(
    providers: list[LLMProvider],
    brief: CompetitionBrief,
    *,
    seeds_per_lane: int = 8,
) -> list[CandidateIdea]:
    """Run lanes independently using only current-competition crowding constraints."""
    if not providers:
        raise ValueError("run_isolated_ideation requires at least one provider")
    template, _ = load_prompt("contrarian-ideation")
    blacklist = _format_blacklist(brief)

    def _run_lane(lane_with_provider: tuple[int, dict[str, Any], LLMProvider]) -> list[CandidateIdea]:
        _, lane, provider = lane_with_provider
        system = render_prompt(
            template,
            {
                "LANE": lane["label"],
                "DISCIPLINES": "\n".join(f"- {discipline}" for discipline in lane["disciplines"]),
                "SANITIZED_BRIEF": brief.sanitized_brief,
                "BLACKLIST": blacklist,
                "SEED_COUNT": str(seeds_per_lane),
            },
        )
        raw = provider.complete_json(system, f"Produce {seeds_per_lane} seeds for lane {lane['id']}.")
        items = raw if isinstance(raw, list) else raw.get("seeds") or raw.get("concepts") or []
        lane_ideas: list[CandidateIdea] = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            idea = _normalize_seed(
                item,
                lane_id=lane["id"],
                disciplines=lane["disciplines"],
                index=index,
            )
            _apply_competition_requirements(idea, brief)
            matched_ban = _matching_competition_ban(idea, brief)
            if matched_ban:
                idea.kill_reason = (idea.kill_reason + f" | competition do-not-build match: {matched_ban}").strip(" |")
                idea.collision_risk = "high"
            lane_ideas.append(idea)
        return lane_ideas

    jobs = [(index, lane, providers[index % len(providers)]) for index, lane in enumerate(IDEATION_LANES)]
    workers = _ideation_workers(len(jobs))
    if workers <= 1:
        lane_results = [_run_lane(job) for job in jobs]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            lane_results = list(pool.map(_run_lane, jobs))

    all_ideas: list[CandidateIdea] = []
    for result in lane_results:
        all_ideas.extend(result)
    return all_ideas


def _ideation_workers(num_lanes: int) -> int:
    raw = os.getenv("HACKFORGE_IDEATION_WORKERS")
    if raw and raw.strip().isdigit():
        return max(1, min(int(raw), num_lanes))
    return min(4, num_lanes)


def _format_blacklist(brief: CompetitionBrief) -> str:
    crowding = brief.crowding
    parts = [
        "HIGH: " + "; ".join(crowding.high_collision),
        "MEDIUM: " + "; ".join(crowding.medium_collision),
        "DO NOT BUILD: " + "; ".join(crowding.do_not_build),
    ]
    return "\n".join(parts)


def _normalize_seed(
    item: dict[str, Any],
    *,
    lane_id: str,
    disciplines: list[str],
    index: int,
) -> CandidateIdea:
    title = item.get("working_title") or item.get("title") or f"{lane_id}-seed-{index}"
    candidate_id = item.get("id") or f"{lane_id}-{slugify(title)}-{index}"
    return CandidateIdea(
        id=candidate_id,
        lane=lane_id,
        disciplines=list(item.get("disciplines") or disciplines),
        working_title=title,
        primary_user=str(item.get("primary_user") or "unspecified stakeholder"),
        painful_workflow=str(item.get("painful_workflow") or ""),
        current_workaround=str(item.get("current_workaround") or ""),
        imported_mechanism=str(item.get("imported_mechanism") or ""),
        mechanism_origin=str(item.get("mechanism_origin") or ""),
        data_sources=list(item.get("data_sources") or []),
        core_computation=str(item.get("core_computation") or ""),
        last_mile_action=str(item.get("last_mile_action") or ""),
        visible_transformation=str(item.get("visible_transformation") or ""),
        sponsor_dependency=str(item.get("sponsor_dependency") or ""),
        technical_risk=str(item.get("technical_risk") or ""),
        collision_risk=item.get("collision_risk") or "unknown",
        why_now=str(item.get("why_now") or ""),
        kill_reason=str(item.get("kill_reason") or ""),
        killer_demo=str(item.get("killer_demo") or ""),
        hard_to_fake_advantage=str(item.get("hard_to_fake_advantage") or ""),
        technology_roles=dict(item.get("technology_roles") or {}),
        requirement_satisfaction=dict(item.get("requirement_satisfaction") or {}),
        data_access_status=str(item.get("data_access_status") or "unverified"),
        data_access_plan=str(item.get("data_access_plan") or ""),
        demo_proof=str(item.get("demo_proof") or item.get("killer_demo") or ""),
        minimum_demonstrable_loop=str(item.get("minimum_demonstrable_loop") or ""),
        track_fit=str(item.get("track_fit") or ""),
    )


def _matching_competition_ban(idea: CandidateIdea, brief: CompetitionBrief) -> str:
    """Return only an evidence-derived current-competition do-not-build match."""
    idea_tokens = set(_norm_tokens(
        " ".join(
            [
                idea.working_title,
                idea.painful_workflow,
                idea.last_mile_action,
                idea.visible_transformation,
                idea.killer_demo,
                idea.imported_mechanism,
            ]
        )
    ))
    if not idea_tokens:
        return ""
    for banned in brief.crowding.do_not_build:
        banned_tokens = set(_norm_tokens(banned))
        if not banned_tokens:
            continue
        overlap = len(idea_tokens & banned_tokens) / max(1, len(banned_tokens))
        if overlap >= 0.5:
            return banned
    return ""


def cluster_ideas(ideas: list[CandidateIdea]) -> list[dict[str, Any]]:
    """Cluster by structural fingerprint (mechanism + action + stakeholder), not title."""
    buckets: dict[str, list[CandidateIdea]] = {}
    for idea in ideas:
        fingerprint = _structural_fingerprint(idea)
        buckets.setdefault(fingerprint, []).append(idea)

    clusters: list[dict[str, Any]] = []
    for index, (fingerprint, members) in enumerate(buckets.items()):
        cluster_id = f"cluster-{index + 1}-{fingerprint[:8]}"
        for member in members:
            member.cluster_id = cluster_id
        clusters.append(
            {
                "cluster_id": cluster_id,
                "fingerprint": fingerprint,
                "size": len(members),
                "member_ids": [member.id for member in members],
                "representative_id": members[0].id,
                "primary_user": members[0].primary_user,
                "imported_mechanism": members[0].imported_mechanism,
                "last_mile_action": members[0].last_mile_action,
            }
        )
    clusters.sort(key=lambda cluster: cluster["size"], reverse=True)
    return clusters


def _structural_fingerprint(idea: CandidateIdea) -> str:
    parts = [
        _norm_tokens(idea.primary_user)[:4],
        _norm_tokens(idea.imported_mechanism)[:6],
        _norm_tokens(idea.last_mile_action)[:4],
        _norm_tokens(idea.core_computation)[:4],
    ]
    joined = "|".join(" ".join(part) for part in parts)
    return hashlib.sha256(joined.encode()).hexdigest()


def _norm_tokens(text: str) -> list[str]:
    stop = {"the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with", "by"}
    return [
        token
        for token in "".join(char.lower() if char.isalnum() else " " for char in text).split()
        if token not in stop
    ]


def select_diversified(
    ideas: list[CandidateIdea],
    clusters: list[dict[str, Any]],
    limit: int = 6,
) -> list[CandidateIdea]:
    """Pick strongest structurally different representatives for collision audit."""
    del clusters
    selected: list[CandidateIdea] = []
    used_fingerprints: set[str] = set()
    ranked = sorted(
        ideas,
        key=lambda idea: (
            0 if idea.collision_risk == "low" else 1 if idea.collision_risk == "medium" else 2,
            0 if idea.hard_to_fake_advantage else 1,
            len(idea.kill_reason),
        ),
    )
    for idea in ranked:
        fingerprint = _structural_fingerprint(idea)
        if fingerprint in used_fingerprints:
            continue
        selected.append(idea)
        used_fingerprints.add(fingerprint)
        if len(selected) >= limit:
            break
    if not selected and ideas:
        selected = ideas[:limit]
    return selected
