from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from hackforge.collision import audit_collisions, collision_markdown
from hackforge.evaluation import (
    blind_judge,
    feasibility_markdown,
    red_team_check,
    review_feasibility,
)
from hackforge.exports import build_decision_dossier
from hackforge.ideation import cluster_ideas, run_isolated_ideation, select_diversified
from hackforge.memory import build_run_manifest
from hackforge.models import CandidateIdea
from hackforge.providers import load_providers
from hackforge.research import (
    build_competition_brief,
    enrich_brief_with_live_crowding,
    ingest_file,
    ingest_url,
    research_markdown,
)
from hackforge.telemetry import trace_stage
from hackforge.utils import env_flag, make_run_dir, sha256_text, write_json, write_text


def run_analyse(
    *,
    input_path: Path | None = None,
    url: str | None = None,
    text: str | None = None,
    dry_run: bool = False,
    fixture_bundle: dict[str, Any] | None = None,
    team_size: str | None = None,
    deadline: str | None = None,
    skills: str | None = None,
    seeds_per_lane: int = 8,
    runs_root: Path | None = None,
    live_research: bool | None = None,
) -> Path:
    if not any([input_path, url, text]):
        raise ValueError("Provide input_path, url, or text")

    providers = load_providers(dry_run=dry_run, fixture_bundle=fixture_bundle)
    do_live = live_research if live_research is not None else (not dry_run and env_flag("HACKFORGE_LIVE_RESEARCH"))
    source_urls: list[str] = []
    if input_path:
        raw, sources = ingest_file(input_path)
        source_urls.extend(sources)
    elif url:
        raw, sources = ingest_url(url)
        source_urls.extend(sources)
    else:
        raw = text or ""
        sources = ["inline"]

    timings: dict[str, float] = {}
    rejections: list[dict[str, str]] = []

    with trace_stage("competition_research", {"dry_run": dry_run}):
        t0 = time.perf_counter()
        brief = build_competition_brief(
            providers.research,
            raw,
            source_urls=source_urls,
            team_size=team_size,
            deadline=deadline,
            skills=skills,
        )
        if do_live:
            enrich_brief_with_live_crowding(brief, force=True)
        timings["competition_research"] = time.perf_counter() - t0

    run_dir = make_run_dir(brief.slug or brief.name, runs_root=runs_root)
    write_json(run_dir / "competition-brief.json", brief.model_dump())
    write_text(run_dir / "verified-research.md", research_markdown(brief))
    write_json(
        run_dir / "crowded-archetypes.json",
        {
            "high_collision": brief.crowding.high_collision,
            "medium_collision": brief.crowding.medium_collision,
            "potentially_underexplored": brief.crowding.potentially_underexplored,
            "do_not_build": brief.crowding.do_not_build,
        },
    )

    with trace_stage("ideation"):
        t0 = time.perf_counter()
        raw_ideas = run_isolated_ideation(
            providers.ideation_lanes,
            brief,
            seeds_per_lane=seeds_per_lane,
        )
        timings["ideation"] = time.perf_counter() - t0
    write_json(run_dir / "raw-concepts.json", [i.model_dump() for i in raw_ideas])

    t0 = time.perf_counter()
    clusters = cluster_ideas(raw_ideas)
    write_json(
        run_dir / "clustered-concepts.json",
        {"clusters": clusters, "ideas": [i.model_dump() for i in raw_ideas]},
    )
    shortlist = select_diversified(raw_ideas, clusters, limit=6)
    timings["cluster"] = time.perf_counter() - t0

    for idea in raw_ideas:
        if idea.id not in {s.id for s in shortlist}:
            rejections.append({"id": idea.id, "reason": idea.kill_reason or "not selected for collision audit"})

    with trace_stage("collision", {"live": do_live}):
        t0 = time.perf_counter()
        collisions = audit_collisions(providers.collision, shortlist, live_enrich=do_live)
        timings["collision"] = time.perf_counter() - t0
    write_text(run_dir / "collision-analysis.md", collision_markdown(collisions))
    write_json(run_dir / "collision-reports.json", [c.model_dump() for c in collisions])

    # Drop hard kills from collision
    survivors = []
    coll_by = {c.candidate_id: c for c in collisions}
    for s in shortlist:
        rep = coll_by.get(s.id)
        if rep and rep.kill_recommendation and rep.collision_risk == "high":
            rejections.append({"id": s.id, "reason": f"collision kill: {rep.notes}"})
        else:
            survivors.append(s)
    if not survivors:
        survivors = shortlist[:3]

    t0 = time.perf_counter()
    feasibility = review_feasibility(providers.feasibility, survivors, brief)
    write_text(run_dir / "feasibility-analysis.md", feasibility_markdown(feasibility))
    write_json(run_dir / "feasibility-reports.json", [f.model_dump() for f in feasibility])
    timings["feasibility"] = time.perf_counter() - t0

    feas_by = {f.candidate_id: f for f in feasibility}
    finalists: list[CandidateIdea] = []
    for s in survivors:
        f = feas_by.get(s.id)
        if f and f.kill_recommendation and f.delivery_risk == "high":
            rejections.append({"id": s.id, "reason": f"feasibility kill: {f.notes}"})
        else:
            finalists.append(s)
    finalists = finalists[:3] or survivors[:3]

    t0 = time.perf_counter()
    evaluation = blind_judge(providers.judges, brief, finalists, collisions, feasibility)
    write_json(run_dir / "blind-judge-results.json", evaluation.model_dump())
    timings["blind_judge"] = time.perf_counter() - t0

    id_by_blind = {c["blind_id"]: c["internal_id"] for c in evaluation.candidates}
    primary_id = id_by_blind[evaluation.recommendation["primary_blind_id"]]
    backup_id = id_by_blind[evaluation.recommendation["backup_blind_id"]]
    primary = next(c for c in finalists if c.id == primary_id)
    backup = next(c for c in finalists if c.id == backup_id)

    t0 = time.perf_counter()
    red = red_team_check(providers.red_team, primary, backup)
    write_json(run_dir / "red-team.json", red)
    if red.get("prefer_backup_instead"):
        primary, backup = backup, primary
    timings["red_team"] = time.perf_counter() - t0

    rejected_ideas = [i for i in raw_ideas if i.id not in {primary.id, backup.id}]
    dossier = build_decision_dossier(
        brief,
        primary,
        backup,
        evaluation,
        collisions,
        feasibility,
        rejected_ideas,
        red,
    )
    write_text(run_dir / "final-recommendation.md", dossier)

    provider_meta = {
        "dry_run": providers.dry_run,
        "research": getattr(providers.research, "name", "unknown"),
        "ideation": [getattr(p, "name", "unknown") for p in providers.ideation_lanes],
        "collision": getattr(providers.collision, "name", "unknown"),
        "feasibility": getattr(providers.feasibility, "name", "unknown"),
        "judges": getattr(providers.judges, "name", "unknown"),
        "models": {
            "research": getattr(providers.research, "model", None),
        },
    }
    build_run_manifest(
        run_dir=run_dir,
        competition_name=brief.name,
        dry_run=providers.dry_run,
        providers=provider_meta,
        input_sources=sources,
        input_hash=sha256_text(raw),
        stage_timings=timings,
        candidate_counts={
            "raw": len(raw_ideas),
            "clusters": len(clusters),
            "collision_shortlist": len(shortlist),
            "finalists": len(finalists),
        },
        rejections=rejections,
        final_primary_id=primary.id,
        final_backup_id=backup.id,
    )
    return run_dir
