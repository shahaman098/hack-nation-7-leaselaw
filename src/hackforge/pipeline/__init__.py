from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from hackforge.collision import audit_collisions, collision_markdown
from hackforge.evaluation import (
    blind_judge,
    evaluate_gates,
    feasibility_markdown,
    gate_failures,
    passes_gates,
    red_team_check,
    review_feasibility,
)
from hackforge.exports import build_decision_dossier, build_idea_landscape
from hackforge.ideation import (
    SparseIdeaArchive,
    cluster_ideas,
    cross_concepts,
    discover_opportunities,
    get_search_profile,
    mine_mechanisms,
    mmr_select,
    mutate_concepts,
    structural_distance,
)
from hackforge.memory import build_run_manifest
from hackforge.models import BuildPlan, CandidateIdea, EvidenceSource, IdeaLineage
from hackforge.profiles import apply_profile_defaults, load_competition_profile, resolve_tracks_fixture
from hackforge.providers import ProviderBundle, load_providers
from hackforge.research import (
    build_competition_brief,
    crawl_competition,
    enrich_brief_with_live_crowding,
    evidence_text,
    ingest_file,
    input_evidence,
    research_markdown,
    search_devpost_projects,
    search_github_projects,
)
from hackforge.run_state import RunJournal
from hackforge.telemetry import trace_stage
from hackforge.utils import env_flag, make_run_dir, sha256_text, write_json, write_text
from hackforge.winners import (
    build_inspiration_report,
    build_winner_patterns,
    filter_training_cutoff,
    inspiration_markdown,
    load_verified_winners,
)

from .build_plan import build_plan_markdown, create_build_plan
from .develop import develop_product


def _run_analyse_impl(
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
    provider: str = "deepseek",
    search_profile: str = "balanced",
    finalists: int = 3,
    visual_report: bool = True,
    collision_excludes: list[str] | None = None,
    execution_providers: ProviderBundle | None = None,
    build_plan: bool = True,
    develop: bool = False,
    competition_profile: str | None = None,
    training_cutoff: str | None = None,
    inspiration_min: float | None = None,
    _journal: RunJournal,
) -> Path:
    del seeds_per_lane  # retained for API compatibility; profiles now own search breadth.
    profile_config = load_competition_profile(competition_profile) if competition_profile else None
    # Profile track pack fills in only when the operator did not already supply
    # competition text (avoids doubling a pasted/official brief with the fixture).
    if profile_config and not any([input_path, url, text]):
        tracks_path = resolve_tracks_fixture(profile_config)
        if tracks_path and tracks_path.exists():
            text, _ = ingest_file(tracks_path)

    if not any([input_path, url, text]):
        raise ValueError("Provide input_path, url, and/or text (they can be combined)")
    if finalists < 3:
        raise ValueError("finalists must be at least 3 (one winner and two structurally different backups)")
    if develop and not build_plan:
        raise ValueError("develop requires build_plan: the development stage implements the generated plan")

    search_profile, finalists, training_cutoff, inspiration_min = (
        apply_profile_defaults(
            profile_config,
            search_profile=search_profile,
            finalists=finalists,
            training_cutoff=training_cutoff,
            inspiration_min=inspiration_min,
        )
        if profile_config
        else (search_profile, finalists, training_cutoff, inspiration_min)
    )
    profile = get_search_profile(search_profile)
    if finalists > profile.judged_finalists:
        raise ValueError(
            f"{search_profile} profile judges at most {profile.judged_finalists} finalists; "
            "choose a broader profile or request fewer outputs"
        )
    run_dir = make_run_dir(_provisional_run_name(input_path, url), runs_root=runs_root)
    _journal.attach(run_dir, provider=provider, search_profile=search_profile)
    _journal.checkpoint("provider_selection")
    providers = execution_providers or load_providers(dry_run=dry_run, fixture_bundle=fixture_bundle, provider=provider)
    if providers.dry_run and os.getenv("HACKFORGE_USE_SENTENCE_TRANSFORMERS") is None:
        os.environ["HACKFORGE_USE_SENTENCE_TRANSFORMERS"] = "0"
    do_live = live_research if live_research is not None else (not providers.dry_run)
    timings: dict[str, float] = {}
    rejections: list[dict[str, str]] = []

    raw, input_sources, evidence = _collect_initial_evidence(input_path=input_path, url=url, text=text)
    source_urls = [source.url for source in evidence if source.source_kind == "official"] or input_sources

    with trace_stage("competition_research", {"dry_run": providers.dry_run}):
        _journal.checkpoint("competition_research")
        t0 = time.perf_counter()
        brief = build_competition_brief(
            providers.research,
            evidence_text(evidence) or raw,
            source_urls=source_urls,
            team_size=team_size,
            deadline=deadline,
            skills=skills,
        )
        if do_live:
            # Public-repository and Devpost discovery are useful collision signals,
            # not universal prerequisites. Sparse/private/non-software competitions
            # must still be analysable. Strict modes remain available explicitly.
            require_github = env_flag("HACKFORGE_REQUIRE_GITHUB_RESEARCH", default=False)
            github_evidence = search_github_projects(
                brief.name,
                token=os.getenv("GITHUB_TOKEN"),
                max_results=12 if search_profile != "fast" else 6,
            )
            github_failures = [source for source in github_evidence if source.fetch_status != "ok"]
            if github_failures and require_github:
                details = "; ".join(
                    f"{source.fetch_status}: {source.error or source.url}" for source in github_failures
                )
                raise RuntimeError(f"Strict GitHub research failed: {details}")
            minimum_github = int(
                os.getenv("HACKFORGE_MIN_GITHUB_RESULTS", "1" if require_github else "0")
            )
            verified_github = [source for source in github_evidence if source.fetch_status == "ok"]
            if len(verified_github) < minimum_github:
                raise RuntimeError(
                    f"GitHub research returned {len(verified_github)} verified repositories; "
                    f"strict mode requires at least {minimum_github}."
                )
            evidence.extend(github_evidence)

            devpost_evidence = search_devpost_projects(
                brief.theme or brief.name,
                max_results=12 if search_profile != "fast" else 6,
            )
            devpost_failures = [source for source in devpost_evidence if source.fetch_status != "ok"]
            require_live_devpost = env_flag("HACKFORGE_REQUIRE_LIVE_DEVPOST", default=False)
            if devpost_failures and require_live_devpost:
                details = "; ".join(
                    f"{source.fetch_status}: {source.error or source.url}" for source in devpost_failures
                )
                raise RuntimeError(f"Strict Devpost research failed: {details}")
            minimum_devpost = int(
                os.getenv("HACKFORGE_MIN_DEVPOST_RESULTS", "1" if require_live_devpost else "0")
            )
            verified_devpost = [source for source in devpost_evidence if source.fetch_status == "ok"]
            if len(verified_devpost) < minimum_devpost:
                raise RuntimeError(
                    f"Devpost research returned {len(verified_devpost)} verified projects; "
                    f"strict mode requires at least {minimum_devpost}."
                )
            # Preserve both successful and failed enrichment attempts as provenance.
            evidence.extend(devpost_evidence)
            if verified_devpost:
                enrich_brief_with_live_crowding(brief, force=True, sources=verified_devpost)
        timings["competition_research"] = time.perf_counter() - t0

    corpus_ref = profile_config.winner_corpus if profile_config else None
    verified_winners = load_verified_winners(str(corpus_ref) if corpus_ref else None)
    verified_winners = filter_training_cutoff(verified_winners, cutoff=training_cutoff)
    with trace_stage("winner_patterns", {"corpus_size": len(verified_winners)}):
        _journal.checkpoint("winner_patterns")
        t0 = time.perf_counter()
        winner_patterns = build_winner_patterns(providers.research, brief, verified_winners)
        timings["winner_patterns"] = time.perf_counter() - t0
    write_json(run_dir / "winner-patterns.json", winner_patterns.model_dump())
    winner_patterns_payload = winner_patterns.model_dump()

    write_json(run_dir / "research-sources.json", [source.model_dump() for source in evidence])
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

    with trace_stage("divergent_search", {"profile": search_profile}):
        _journal.checkpoint("divergent_search")
        t0 = time.perf_counter()
        _journal.checkpoint("opportunity_discovery", requested=profile.opportunities)
        opportunities = discover_opportunities(
            providers.research,
            brief,
            evidence,
            profile.opportunities,
            winner_patterns=winner_patterns_payload,
        )
        _journal.checkpoint("mechanism_mining", requested=profile.mechanisms)
        mechanisms = mine_mechanisms(providers.ideation_lanes[0], brief, profile.mechanisms)
        _journal.checkpoint("concept_crossing", requested=profile.initial_concepts)
        ideas, lineage = cross_concepts(
            providers.ideation_lanes[1 % len(providers.ideation_lanes)],
            brief,
            opportunities,
            mechanisms,
            profile.initial_concepts,
            evidence=evidence,
            winner_patterns=winner_patterns_payload,
        )
        archive = SparseIdeaArchive()
        for idea in ideas:
            archive.insert(idea)
        for round_number in range(1, profile.mutation_rounds + 1):
            _journal.checkpoint(
                f"mutation_round_{round_number}",
                requested=profile.mutations_per_round,
            )
            targets = archive.empty_region_targets(profile.mutations_per_round)
            parents = archive.elites() or ideas
            mutations, new_lineage = mutate_concepts(
                providers.ideation_lanes[round_number % len(providers.ideation_lanes)],
                brief,
                parents,
                opportunities,
                mechanisms,
                round_number=round_number,
                count=profile.mutations_per_round,
                targets=targets,
                evidence=evidence,
            )
            ideas.extend(mutations)
            lineage.extend(new_lineage)
            for idea in mutations:
                archive.insert(idea)
        timings["divergent_search"] = time.perf_counter() - t0

    write_json(run_dir / "opportunity-cards.json", [card.model_dump() for card in opportunities])
    write_json(run_dir / "mechanism-cards.json", [card.model_dump() for card in mechanisms])
    write_json(run_dir / "raw-concepts.json", [idea.model_dump() for idea in ideas])
    write_json(run_dir / "idea-archive.json", archive.export())
    write_json(run_dir / "search-lineage.json", [item.model_dump() for item in lineage])
    clusters = cluster_ideas(ideas)
    write_json(
        run_dir / "clustered-concepts.json",
        {"clusters": clusters, "ideas": [idea.model_dump() for idea in ideas]},
    )

    t0 = time.perf_counter()
    _journal.checkpoint("hard_gates", candidates=len(ideas))
    gated = _run_gates(ideas, brief, evidence, rejections)
    if not gated:
        _journal.checkpoint("hard_gate_repair", candidates=len(ideas), requested=8)
        emergency, emergency_lineage = _emergency_mutation(
            providers,
            brief,
            ideas,
            opportunities,
            mechanisms,
            archive,
            evidence,
            round_number=profile.mutation_rounds + 1,
        )
        ideas.extend(emergency)
        lineage.extend(emergency_lineage)
        for idea in emergency:
            archive.insert(idea)
        gated = _run_gates(emergency, brief, evidence, rejections)
        _rewrite_search_artifacts(run_dir, ideas, lineage, archive)
    if not gated:
        write_json(run_dir / "gate-results.json", _gate_payload(ideas))
        raise RuntimeError("Every candidate failed one or more applicable competition requirements")
    write_json(run_dir / "gate-results.json", _gate_payload(ideas))
    timings["hard_gates"] = time.perf_counter() - t0

    shortlist = mmr_select(gated, profile.collision_shortlist, minimum_distance=0.22)
    selected_ids = {idea.id for idea in shortlist}
    for idea in ideas:
        if idea.id not in selected_ids and not any(item["id"] == idea.id for item in rejections):
            rejections.append({"id": idea.id, "reason": "outcompeted in quality-diversity/MMR selection"})

    with trace_stage("collision", {"live": do_live}):
        _journal.checkpoint("collision_audit", candidates=len(shortlist))
        t0 = time.perf_counter()
        collisions = audit_collisions(
            providers.collision,
            shortlist,
            corpus=_public_analogues(evidence),
            live_enrich=False,
            exclude=collision_excludes,
        )
        timings["collision"] = time.perf_counter() - t0
    write_text(run_dir / "collision-analysis.md", collision_markdown(collisions))
    write_json(run_dir / "collision-reports.json", [report.model_dump() for report in collisions])
    collision_by = {report.candidate_id: report for report in collisions}
    survivors = []
    for idea in shortlist:
        report = collision_by.get(idea.id)
        if report and report.collision_risk == "high" and report.kill_recommendation:
            rejections.append(
                {"id": idea.id, "reason": f"collision kill: {report.notes or 'structural analogue'}"}
            )
        else:
            survivors.append(idea)
    if not survivors:
        survivors, added_collisions, added_lineage = _repair_all_killed(
            providers,
            brief,
            shortlist,
            opportunities,
            mechanisms,
            archive,
            evidence,
            profile.mutation_rounds + 2,
            collision_excludes,
        )
        collisions.extend(added_collisions)
        lineage.extend(added_lineage)
    if not survivors:
        raise RuntimeError("All collision-audited candidates failed; repair mutations also failed")

    t0 = time.perf_counter()
    _journal.checkpoint("feasibility", candidates=len(survivors))
    feasibility = review_feasibility(providers.feasibility, survivors, brief)
    write_text(run_dir / "feasibility-analysis.md", feasibility_markdown(feasibility))
    write_json(run_dir / "feasibility-reports.json", [report.model_dump() for report in feasibility])
    timings["feasibility"] = time.perf_counter() - t0
    feasibility_by = {report.candidate_id: report for report in feasibility}
    feasible = []
    for idea in survivors:
        feasibility_report = feasibility_by.get(idea.id)
        if (
            feasibility_report
            and feasibility_report.delivery_risk == "high"
            and feasibility_report.kill_recommendation
        ):
            rejections.append(
                {"id": idea.id, "reason": f"feasibility kill: {feasibility_report.notes}"}
            )
        else:
            feasible.append(idea)
    required_finalists = min(finalists, 3)
    if len(feasible) < required_finalists:
        repair_ideas, repair_lineage = _emergency_mutation(
            providers,
            brief,
            survivors,
            opportunities,
            mechanisms,
            archive,
            evidence,
            round_number=profile.mutation_rounds + 3,
        )
        lineage.extend(repair_lineage)
        repair_gated = _run_gates(repair_ideas, brief, evidence, rejections)
        for idea in repair_ideas:
            ideas.append(idea)
            archive.insert(idea)
        repair_collisions = (
            audit_collisions(
                providers.collision,
                repair_gated,
                corpus=_public_analogues(evidence),
                live_enrich=False,
                exclude=collision_excludes,
            )
            if repair_gated
            else []
        )
        collisions.extend(repair_collisions)
        repair_collision_by = {report.candidate_id: report for report in repair_collisions}
        repair_survivors = [
            idea
            for idea in repair_gated
            if not (
                repair_collision_by.get(idea.id)
                and repair_collision_by[idea.id].collision_risk == "high"
                and repair_collision_by[idea.id].kill_recommendation
            )
        ]
        repair_feasibility = (
            review_feasibility(providers.feasibility, repair_survivors, brief)
            if repair_survivors
            else []
        )
        feasibility.extend(repair_feasibility)
        repair_feasibility_by = {report.candidate_id: report for report in repair_feasibility}
        repair_feasible = [
            idea
            for idea in repair_survivors
            if not (
                repair_feasibility_by.get(idea.id)
                and repair_feasibility_by[idea.id].delivery_risk == "high"
                and repair_feasibility_by[idea.id].kill_recommendation
            )
        ]
        existing_ids = {idea.id for idea in feasible}
        feasible.extend(idea for idea in repair_feasible if idea.id not in existing_ids)
        _rewrite_search_artifacts(run_dir, ideas, lineage, archive)
        write_text(run_dir / "collision-analysis.md", collision_markdown(collisions))
        write_json(run_dir / "collision-reports.json", [report.model_dump() for report in collisions])
        write_text(run_dir / "feasibility-analysis.md", feasibility_markdown(feasibility))
        write_json(run_dir / "feasibility-reports.json", [report.model_dump() for report in feasibility])
    if not feasible:
        raise RuntimeError("All candidates and feasibility-repair mutations failed independent review")

    judged = mmr_select(feasible, min(profile.judged_finalists, len(feasible)), minimum_distance=0.20)
    if len(judged) < required_finalists:
        raise RuntimeError("Fewer than three structurally viable finalists survived fail-closed evaluation")

    inspiration_report = build_inspiration_report(
        judged,
        verified_winners,
        inspiration_min=inspiration_min,
        training_cutoff=training_cutoff,
    )
    write_json(run_dir / "inspiration-report.json", inspiration_report.model_dump())
    for row in inspiration_report.candidates:
        if row.clone_guard:
            rejections.append(
                {
                    "id": row.candidate_id,
                    "reason": "inspiration clone guard: user/problem/mechanism alignment too high vs verified winner",
                }
            )

    t0 = time.perf_counter()
    _journal.checkpoint("blind_judging", candidates=len(judged))
    evaluation = blind_judge(providers.judges, brief, judged, collisions, feasibility)
    write_json(run_dir / "blind-judge-results.json", evaluation.model_dump())
    timings["blind_judge"] = time.perf_counter() - t0

    id_by_blind = {row["blind_id"]: row["internal_id"] for row in evaluation.candidates}
    primary_id = id_by_blind[evaluation.recommendation["primary_blind_id"]]
    backup_id = id_by_blind[evaluation.recommendation["backup_blind_id"]]
    primary = next(idea for idea in judged if idea.id == primary_id)
    judge_backup = next(idea for idea in judged if idea.id == backup_id)
    outputs = _select_outputs(primary, judge_backup, judged, min(finalists, len(judged)))

    t0 = time.perf_counter()
    red = red_team_check(providers.red_team, outputs[0], outputs[1])
    write_json(run_dir / "red-team.json", red)
    if red.get("prefer_backup_instead"):
        outputs[0], outputs[1] = outputs[1], outputs[0]
    timings["red_team"] = time.perf_counter() - t0

    plan: BuildPlan | None = None
    if build_plan:
        _journal.checkpoint("build_plan", candidates=1)
        t0 = time.perf_counter()
        selected_feasibility = next(
            (report for report in feasibility if report.candidate_id == outputs[0].id), None
        )
        if selected_feasibility is None:
            raise RuntimeError("Selected primary has no existing feasibility report for build planning")
        plan = create_build_plan(providers.feasibility, brief, outputs[0], selected_feasibility, red)
        write_json(run_dir / "build-plan.json", plan.model_dump())
        write_text(run_dir / "build-plan.md", build_plan_markdown(plan))
        timings["build_plan"] = time.perf_counter() - t0

    if develop:
        if plan is None:
            raise RuntimeError("Development stage requires a generated build plan")
        _journal.checkpoint("development", tasks=len(plan.tasks))
        t0 = time.perf_counter()
        dev_report = develop_product(providers.feasibility, brief, plan, run_dir / "product")
        write_json(run_dir / "development-report.json", dev_report.model_dump())
        timings["develop"] = time.perf_counter() - t0

    output_ids = {idea.id for idea in outputs}
    rejected_ideas = [idea for idea in ideas if idea.id not in output_ids]
    dossier = build_decision_dossier(
        brief,
        outputs[0],
        outputs[1] if len(outputs) > 1 else outputs[0],
        evaluation,
        collisions,
        feasibility,
        rejected_ideas,
        red,
    )
    if len(outputs) > 2:
        dossier += (
            f"\n\n## Structurally different backup 2\n**{outputs[2].working_title}** (`{outputs[2].id}`)\n"
            f"- Stakeholder: {outputs[2].primary_user}\n"
            f"- Mechanism: {outputs[2].imported_mechanism}\n"
            f"- Proof/demo: {outputs[2].killer_demo}\n"
        )
    dossier += "\n\n" + inspiration_markdown(
        inspiration_report,
        titles_by_id={idea.id: idea.working_title for idea in judged},
    )
    write_text(run_dir / "final-recommendation.md", dossier)

    if visual_report:
        _journal.checkpoint("exporting", finalists=len(outputs))
        write_text(
            run_dir / "idea-landscape.html",
            build_idea_landscape(
                brief=brief,
                sources=evidence,
                opportunities=opportunities,
                mechanisms=mechanisms,
                archive=archive.export(),
                lineage=lineage,
                collisions=collisions,
                evaluation=evaluation,
                outputs=outputs,
                rejected=rejections,
            ),
        )

    provider_meta = {
        "dry_run": providers.dry_run,
        "selection": provider,
        "research": getattr(providers.research, "name", "unknown"),
        "ideation": [getattr(item, "name", "unknown") for item in providers.ideation_lanes],
        "collision": getattr(providers.collision, "name", "unknown"),
        "feasibility": getattr(providers.feasibility, "name", "unknown"),
        "build_plan": getattr(providers.feasibility, "name", "unknown") if build_plan else None,
        "develop": getattr(providers.feasibility, "name", "unknown") if develop else None,
        "judges": getattr(providers.judges, "name", "unknown"),
        "models": {"research": getattr(providers.research, "model", None)},
        "requested_models": {"research": getattr(providers.research, "requested_model", None)},
        "usage": (
            providers.research.usage_snapshot()
            if hasattr(providers.research, "usage_snapshot")
            else None
        ),
    }
    manifest = build_run_manifest(
        run_dir=run_dir,
        competition_name=brief.name,
        dry_run=providers.dry_run,
        providers=provider_meta,
        input_sources=input_sources,
        input_hash=sha256_text(raw),
        stage_timings=timings,
        candidate_counts={
            "raw": len(ideas),
            "archive_cells": len(archive.cells),
            "collision_shortlist": len(shortlist),
            "judged_finalists": len(judged),
            "finalists": len(outputs),
        },
        rejections=rejections,
        final_primary_id=outputs[0].id,
        final_backup_id=outputs[1].id if len(outputs) > 1 else None,
    )
    manifest.update(
        {
            "search_profile": search_profile,
            "target_evaluated_concepts": profile.evaluated_concepts,
            "final_output_ids": [idea.id for idea in outputs],
            "visual_report": visual_report,
            "build_plan": build_plan,
            "develop": develop,
            "optional_stage_call_budget": {"build_plan": int(build_plan), "develop": int(develop)},
            "competition_profile": competition_profile,
            "inspiration_min": inspiration_min,
            "training_cutoff": training_cutoff,
            "winner_patterns_version": "v1",
            "inspiration_summary": {
                "corpus_size": inspiration_report.corpus_size,
                "flagged_finalists": sum(1 for row in inspiration_report.candidates if row.flagged),
                "clone_guard_hits": sum(1 for row in inspiration_report.candidates if row.clone_guard),
            },
        }
    )
    write_json(run_dir / "run-manifest.json", manifest)
    _journal.complete(output_ids=[idea.id for idea in outputs])
    return run_dir


def _collect_initial_evidence(
    *, input_path: Path | None, url: str | None, text: str | None
) -> tuple[str, list[str], list[EvidenceSource]]:
    """Merge operator file/paste and optional URL crawl into one evidence pack.

    Sources are complementary, not mutually exclusive: a pasted description can
    fill gaps left by a JS-heavy or blocked competition page, and a URL can add
    official pages even when the operator already pasted the brief.
    Operator-supplied material is ordered first so it stays authoritative.
    """
    evidence: list[EvidenceSource] = []
    input_sources: list[str] = []
    raw_parts: list[str] = []

    if input_path is not None:
        file_raw, sources = ingest_file(input_path)
        if file_raw.strip():
            raw_parts.append(file_raw)
            input_sources.extend(sources)
            evidence.append(input_evidence(file_raw, sources[0]))

    if text is not None and text.strip():
        raw_parts.append(text)
        input_sources.append("inline")
        evidence.append(input_evidence(text, "inline"))

    url_failed_without_fallback = False
    if url:
        crawled = crawl_competition(url)
        crawled_text = evidence_text(crawled)
        evidence.extend(crawled)
        input_sources.append(url)
        if crawled_text.strip():
            raw_parts.append(crawled_text)
        elif not raw_parts:
            url_failed_without_fallback = True

    if url_failed_without_fallback:
        raise RuntimeError(
            f"Could not retrieve competition evidence from {url}. "
            "Paste the official description with --text or --input and keep --url as a citation."
        )

    raw = "\n\n".join(part for part in raw_parts if part.strip())
    if not raw.strip():
        raise RuntimeError(
            "No usable competition description found. "
            "Provide --url, --text, and/or --input with real content."
        )
    return raw, input_sources, evidence


def _run_gates(
    ideas: list[CandidateIdea],
    brief: Any,
    evidence: list[EvidenceSource],
    rejections: list[dict[str, str]],
) -> list[CandidateIdea]:
    passing = []
    known_rejections = {row["id"] for row in rejections}
    for idea in ideas:
        evaluate_gates(idea, brief, evidence)
        if passes_gates(idea):
            passing.append(idea)
        elif idea.id not in known_rejections:
            rejections.append(
                {"id": idea.id, "reason": "gate failure: " + ", ".join(gate_failures(idea))}
            )
    return passing


def _emergency_mutation(
    providers: ProviderBundle,
    brief: Any,
    parents: list[CandidateIdea],
    opportunities: list[Any],
    mechanisms: list[Any],
    archive: SparseIdeaArchive,
    evidence: list[EvidenceSource],
    *,
    round_number: int,
) -> tuple[list[CandidateIdea], list[IdeaLineage]]:
    repair_targets = [
        f"repair every failed applicable gate; also diversify toward {region}"
        for region in archive.empty_region_targets(8)
    ]
    return mutate_concepts(
        providers.ideation_lanes[round_number % len(providers.ideation_lanes)],
        brief,
        parents,
        opportunities,
        mechanisms,
        round_number=round_number,
        count=8,
        targets=repair_targets,
        evidence=evidence,
    )


def _repair_all_killed(
    providers: ProviderBundle,
    brief: Any,
    parents: list[CandidateIdea],
    opportunities: list[Any],
    mechanisms: list[Any],
    archive: SparseIdeaArchive,
    evidence: list[EvidenceSource],
    round_number: int,
    collision_excludes: list[str] | None = None,
) -> tuple[list[CandidateIdea], list[Any], list[IdeaLineage]]:
    mutations, lineage = _emergency_mutation(
        providers,
        brief,
        parents,
        opportunities,
        mechanisms,
        archive,
        evidence,
        round_number=round_number,
    )
    gated = []
    for idea in mutations:
        evaluate_gates(idea, brief, evidence)
        if passes_gates(idea):
            gated.append(idea)
            archive.insert(idea)
    collisions = (
        audit_collisions(
            providers.collision,
            gated,
            corpus=_public_analogues(evidence),
            live_enrich=False,
            exclude=collision_excludes,
        )
        if gated
        else []
    )
    reports = {report.candidate_id: report for report in collisions}
    survivors = [
        idea
        for idea in gated
        if not (
            reports.get(idea.id)
            and reports[idea.id].collision_risk == "high"
            and reports[idea.id].kill_recommendation
        )
    ]
    return survivors, collisions, lineage


def _select_outputs(
    primary: CandidateIdea,
    judge_backup: CandidateIdea,
    judged: list[CandidateIdea],
    count: int,
) -> list[CandidateIdea]:
    output = [primary]
    pool = [judge_backup] + [
        idea for idea in judged if idea.id not in {primary.id, judge_backup.id}
    ]
    while pool and len(output) < count:
        eligible = [
            idea
            for idea in pool
            if min(structural_distance(idea, chosen) for chosen in output) >= 0.22
        ]
        candidates = eligible or pool
        pick = max(
            candidates,
            key=lambda idea: min(structural_distance(idea, chosen) for chosen in output),
        )
        output.append(pick)
        pool = [idea for idea in pool if idea.id != pick.id]
    return output


def _gate_payload(ideas: list[CandidateIdea]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": idea.id,
            "passed": passes_gates(idea),
            "results": [result.model_dump() for result in idea.gate_results],
            "external_evaluation_scores": idea.external_evaluation_scores,
        }
        for idea in ideas
    ]


def _rewrite_search_artifacts(
    run_dir: Path,
    ideas: list[CandidateIdea],
    lineage: list[IdeaLineage],
    archive: SparseIdeaArchive,
) -> None:
    write_json(run_dir / "raw-concepts.json", [idea.model_dump() for idea in ideas])
    write_json(run_dir / "idea-archive.json", archive.export())
    write_json(run_dir / "search-lineage.json", [item.model_dump() for item in lineage])


def _public_analogues(evidence: list[EvidenceSource]) -> list[dict[str, Any]]:
    return [
        {
            "name": source.title,
            "source": source.source_kind,
            "url": source.url,
            "user": "public-project stakeholders",
            "problem": source.excerpt,
            "mechanism": source.excerpt,
            "data": "",
            "action": "",
            "demo": source.excerpt,
        }
        for source in evidence
        if source.source_kind in {"github", "devpost", "corpus"} and source.fetch_status == "ok"
    ]


def _provisional_run_name(input_path: Path | None, url: str | None) -> str:
    if input_path:
        return input_path.stem
    if url:
        parsed = urlparse(url)
        return parsed.netloc or "competition-url"
    return "inline-competition"


def run_analyse(**kwargs: Any) -> Path:
    """Run a journaled analysis; partial runs remain inspectable after failure or cancellation."""
    journal = RunJournal()
    try:
        return _run_analyse_impl(_journal=journal, **kwargs)
    except KeyboardInterrupt as exc:
        journal.fail(exc)
        raise
    except Exception as exc:
        journal.fail(exc)
        location = f" Partial run: {journal.run_dir}." if journal.run_dir else ""
        log = f" Failure log: {journal.run_dir / 'run.log'}." if journal.run_dir else ""
        raise RuntimeError(f"{exc}{location}{log}") from exc
