from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from hackforge.models import CandidateIdea, CompetitionBrief
from hackforge.paths import IDEATION_LANES
from hackforge.providers import LLMProvider
from hackforge.utils import load_prompt, render_prompt, slugify

from .search import (
    SEARCH_PROFILES as SEARCH_PROFILES,
)
from .search import (
    SparseIdeaArchive as SparseIdeaArchive,
)
from .search import (
    cross_concepts as cross_concepts,
)
from .search import (
    discover_opportunities as discover_opportunities,
)
from .search import (
    external_quality as external_quality,
)
from .search import (
    get_search_profile as get_search_profile,
)
from .search import (
    mine_mechanisms as mine_mechanisms,
)
from .search import (
    mmr_select as mmr_select,
)
from .search import (
    mutate_concepts as mutate_concepts,
)
from .search import (
    structural_distance as structural_distance,
)

NAVIGATOR_TOKENS = (
    "navigator",
    "opportunity board",
    "eligibility checker",
    "application draft",
    "crisis action plan",
    "safe route",
    "campaign fatigue",
    "ops doctor",
)


def run_isolated_ideation(
    providers: list[LLMProvider],
    brief: CompetitionBrief,
    *,
    seeds_per_lane: int = 8,
) -> list[CandidateIdea]:
    """Run lanes independently. Callers must not share prior lane outputs across providers.

    Lanes are isolated by construction (each gets its own provider + prompt and never sees
    another lane's output), so they can run concurrently. Results are reassembled in lane
    order to keep runs reproducible. Set ``HACKFORGE_IDEATION_WORKERS`` to control parallelism
    (tests can force serial execution; live runs default to four workers).
    """
    template, _ = load_prompt("contrarian-ideation")
    blacklist = _format_blacklist(brief)

    def _run_lane(lane_with_provider: tuple[int, dict[str, Any], LLMProvider]) -> list[CandidateIdea]:
        _, lane, provider = lane_with_provider
        system = render_prompt(
            template,
            {
                "LANE": lane["label"],
                "DISCIPLINES": "\n".join(f"- {d}" for d in lane["disciplines"]),
                "SANITIZED_BRIEF": brief.sanitized_brief,
                "BLACKLIST": blacklist,
                "SEED_COUNT": str(seeds_per_lane),
            },
        )
        raw = provider.complete_json(system, f"Produce {seeds_per_lane} seeds for lane {lane['id']}.")
        items = raw if isinstance(raw, list) else raw.get("seeds") or raw.get("concepts") or []
        lane_ideas: list[CandidateIdea] = []
        for n, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            idea = _normalize_seed(item, lane_id=lane["id"], disciplines=lane["disciplines"], index=n)
            if _violates_hard_bans(idea):
                idea.kill_reason = (idea.kill_reason + " | hard-ban topology").strip(" |")
                idea.collision_risk = "high"
            lane_ideas.append(idea)
        return lane_ideas

    jobs = [(idx, lane, providers[idx % len(providers)]) for idx, lane in enumerate(IDEATION_LANES)]
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
    c = brief.crowding
    parts = [
        "HIGH: " + "; ".join(c.high_collision),
        "MEDIUM: " + "; ".join(c.medium_collision),
        "DO NOT BUILD: " + "; ".join(c.do_not_build),
    ]
    return "\n".join(parts)


def _normalize_seed(item: dict[str, Any], *, lane_id: str, disciplines: list[str], index: int) -> CandidateIdea:
    title = item.get("working_title") or item.get("title") or f"{lane_id}-seed-{index}"
    cid = item.get("id") or f"{lane_id}-{slugify(title)}-{index}"
    return CandidateIdea(
        id=cid,
        lane=lane_id,
        disciplines=list(item.get("disciplines") or disciplines),
        working_title=title,
        primary_user=str(item.get("primary_user") or "unspecified"),
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
    )


def _violates_hard_bans(idea: CandidateIdea) -> bool:
    blob = " ".join(
        [
            idea.working_title,
            idea.painful_workflow,
            idea.last_mile_action,
            idea.visible_transformation,
            idea.killer_demo,
            idea.imported_mechanism,
        ]
    ).lower()
    if any(tok in blob for tok in NAVIGATOR_TOKENS):
        # Soft structural twin detection for known mega-archetypes
        recover = ("eligib" in blob and "draft" in blob) or ("rank" in blob and "application" in blob)
        crisis = ("heatwave" in blob or "air quality" in blob) and ("safe" in blob or "action plan" in blob)
        ops = ("campaign" in blob and "fatigue" in blob) or ("ctr" in blob and "ad copy" in blob)
        return recover or crisis or ops
    banned_words = ("tutor", "summarizer", "summariser", "wellness bot", "resume optim")
    return any(w in blob for w in banned_words)


def cluster_ideas(ideas: list[CandidateIdea]) -> list[dict[str, Any]]:
    """Cluster by structural fingerprint (mechanism + action + user class), not title."""
    buckets: dict[str, list[CandidateIdea]] = {}
    for idea in ideas:
        fp = _structural_fingerprint(idea)
        buckets.setdefault(fp, []).append(idea)

    clusters: list[dict[str, Any]] = []
    for i, (fp, members) in enumerate(buckets.items()):
        cid = f"cluster-{i+1}-{fp[:8]}"
        for m in members:
            m.cluster_id = cid
        clusters.append(
            {
                "cluster_id": cid,
                "fingerprint": fp,
                "size": len(members),
                "member_ids": [m.id for m in members],
                "representative_id": members[0].id,
                "primary_user": members[0].primary_user,
                "imported_mechanism": members[0].imported_mechanism,
                "last_mile_action": members[0].last_mile_action,
            }
        )
    clusters.sort(key=lambda c: c["size"], reverse=True)
    return clusters


def _structural_fingerprint(idea: CandidateIdea) -> str:
    parts = [
        _norm_tokens(idea.primary_user)[:4],
        _norm_tokens(idea.imported_mechanism)[:6],
        _norm_tokens(idea.last_mile_action)[:4],
        _norm_tokens(idea.core_computation)[:4],
    ]
    joined = "|".join(" ".join(p) for p in parts)
    return hashlib.sha256(joined.encode()).hexdigest()


def _norm_tokens(text: str) -> list[str]:
    stop = {"the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with", "by"}
    tokens = [t for t in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if t not in stop]
    return tokens


def select_diversified(ideas: list[CandidateIdea], clusters: list[dict[str, Any]], limit: int = 6) -> list[CandidateIdea]:
    """Pick strongest structurally different representatives for collision audit."""
    del clusters  # ranking derives structure directly from ideas
    selected: list[CandidateIdea] = []
    used_fps: set[str] = set()
    # Prefer clusters with clearer hard-to-fake advantage and lower self-stated kill pressure
    ranked = sorted(
        ideas,
        key=lambda x: (
            0 if x.collision_risk == "low" else 1 if x.collision_risk == "medium" else 2,
            0 if x.hard_to_fake_advantage else 1,
            len(x.kill_reason),
        ),
    )
    for idea in ranked:
        fp = _structural_fingerprint(idea)
        if fp in used_fps:
            continue
        selected.append(idea)
        used_fps.add(fp)
        if len(selected) >= limit:
            break
    # Ensure we never return empty if ideas exist
    if not selected and ideas:
        selected = ideas[:limit]
    return selected
