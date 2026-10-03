"""Offline scoring and leakage-controlled winner backtests.

The decision rule and matcher are fixed before any live results are collected.
Lexical overlap is a proxy, not proof of semantic equivalence.
"""
from __future__ import annotations

import os
import random
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from hackforge.evals.benchmark import naive_baseline
from hackforge.evaluation import _weighted_official_score
from hackforge.models import CompetitionBrief, EvaluationResult
from hackforge.paths import EVALS_DIR, FIXTURES_DIR, REPO_ROOT
from hackforge.pipeline import run_analyse
from hackforge.providers import load_providers
from hackforge.utils import env_flag, read_json, write_json, write_text

DECISION_RULE = (
    "On verified post-cutoff cases, pipeline recall@3 must strictly exceed shuffled, "
    "fixture-naive and live-naive controls; otherwise rework judging before adding stages."
)
THRESHOLD = 0.30


@contextmanager
def fixture_distance_mode(enabled: bool) -> Iterator[None]:
    """Fixture orchestration must not download models; restore operator settings."""
    key = "HACKFORGE_USE_SENTENCE_TRANSFORMERS"
    previous = os.environ.get(key)
    if enabled:
        os.environ[key] = "0"
    try:
        yield
    finally:
        if enabled:
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = read_json(path)
    if not isinstance(cases, list) or not cases:
        raise ValueError("Cases must be a nonempty JSON list")
    slugs: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or not case.get("slug") or not case.get("brief_path"):
            raise ValueError("Each case needs slug and brief_path")
        if case["slug"] in slugs:
            raise ValueError("Duplicate case slug")
        slugs.add(case["slug"])
        if case.get("cutoff_class", "unknown") not in {"pre-cutoff", "post-cutoff", "unknown"}:
            raise ValueError("cutoff_class must be pre-cutoff, post-cutoff or unknown")
        if case.get("cutoff_class") in {"pre-cutoff", "post-cutoff"} and not case.get("synthetic"):
            if not case.get("cutoff_note"):
                raise ValueError("Real pre/post-cutoff cases require a documented model cutoff_note")
        for winner in case.get("winners", []):
            if not all(winner.get(key) for key in ("title", "user", "problem", "mechanism")):
                raise ValueError("Winners need title, user, problem and mechanism")
    return cases


def total_order(run_dir: Path) -> list[dict[str, Any]]:
    raw = read_json(run_dir / "raw-concepts.json")
    by_id = {idea["id"]: idea for idea in raw}
    gates = {row["candidate_id"]: row for row in read_json(run_dir / "gate-results.json")}
    manifest = read_json(run_dir / "run-manifest.json")
    evaluation = EvaluationResult.model_validate(read_json(run_dir / "blind-judge-results.json"))
    brief = CompetitionBrief.model_validate(read_json(run_dir / "competition-brief.json"))
    collisions = read_json(run_dir / "collision-reports.json")
    feasibility = read_json(run_dir / "feasibility-reports.json")
    killed = {
        row["candidate_id"] for row in collisions + feasibility
        if row.get("kill_recommendation")
        and (row.get("collision_risk") == "high" or row.get("delivery_risk") == "high")
    }
    result: list[dict[str, Any]] = []
    seen: set[str] = set()

    def take(ids: list[str]) -> None:
        for idea_id in ids:
            if idea_id in by_id and idea_id not in seen:
                result.append(by_id[idea_id])
                seen.add(idea_id)

    def quality(idea_id: str) -> tuple[float, str]:
        scores = gates.get(idea_id, {}).get("external_evaluation_scores", {})
        values = [float(value) for value in scores.values() if isinstance(value, (int, float))]
        return (-sum(values) / max(1, len(values)), idea_id)

    take(manifest.get("final_output_ids", []))
    judged = sorted(
        evaluation.candidates,
        key=lambda row: (-_weighted_official_score(evaluation.judge_votes, row["blind_id"], brief), row["internal_id"]),
    )
    take([row["internal_id"] for row in judged if row["internal_id"] not in killed])
    take(sorted([row["candidate_id"] for row in collisions if row["candidate_id"] not in killed], key=quality))
    take(sorted([idea_id for idea_id, gate in gates.items() if gate["passed"] and idea_id not in killed], key=quality))
    take(sorted(by_id, key=quality))
    return result


def match_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return " ".join(str(value.get(left) or value.get(right) or "") for left, right in (
        ("primary_user", "user"), ("painful_workflow", "problem"), ("imported_mechanism", "mechanism"),
    ))


def similarity_matrix(ideas: list[Any], winners: list[dict[str, Any]], scorer: str = "token") -> list[list[float]]:
    texts = [match_text(value) for value in ideas + winners]
    if scorer == "embed":
        from hackforge.collision.embed_index import EmbedIndex

        vectors = EmbedIndex().encode(texts)
        return [[float(vectors[i] @ vectors[len(ideas) + j]) for j in range(len(winners))] for i in range(len(ideas))]
    tokens = [{token for token in re.findall(r"\w+", text.casefold()) if len(token) > 3} for text in texts]
    return [[len(tokens[i] & tokens[len(ideas) + j]) / max(1, len(tokens[i] | tokens[len(ideas) + j]))
             for j in range(len(winners))] for i in range(len(ideas))]


def score_order(scores: list[list[float]], winners: list[dict[str, Any]], threshold: float = THRESHOLD) -> dict[str, Any]:
    ranks = [next((i + 1 for i, row in enumerate(scores) if row[j] >= threshold), None) for j in range(len(winners))]
    count = len(winners)
    return {
        "recall_at_3": sum(rank is not None and rank <= 3 for rank in ranks) / max(1, count),
        "recall_at_12": sum(rank is not None and rank <= 12 for rank in ranks) / max(1, count),
        "mrr": sum(1 / rank for rank in ranks if rank is not None) / max(1, count),
        "winners": [{"title": winner["title"], "first_match_rank": rank,
                     "best_score": max((row[j] for row in scores), default=0.0),
                     "best_match_rank": max(range(len(scores)), key=lambda i: scores[i][j]) + 1 if scores else None}
                    for j, (winner, rank) in enumerate(zip(winners, ranks))],
    }


def shuffled_control(scores: list[list[float]], winners: list[dict[str, Any]], threshold: float = THRESHOLD,
                     *, trials: int = 200, seed: int = 17) -> dict[str, Any]:
    if trials < 1:
        raise ValueError("trials must be positive")
    rng = random.Random(seed)
    samples = []
    for _ in range(trials):
        shuffled = list(scores)
        rng.shuffle(shuffled)
        samples.append(score_order(shuffled, winners, threshold))
    return {**{key: sum(sample[key] for sample in samples) / trials for key in ("recall_at_3", "recall_at_12", "mrr")},
            "trials": trials, "seed": seed}


def run_backtest(cases_path: Path, *, provider: str = "fixture", live: bool = False,
                 max_cases: int | None = None, results_dir: Path | None = None,
                 scorer: str = "token", threshold: float = THRESHOLD,
                 case_slugs: tuple[str, ...] = ()) -> Path:
    if scorer not in {"token", "embed"} or not 0 <= threshold <= 1:
        raise ValueError("Invalid scorer or threshold")
    if provider not in {"fixture", "codex", "deepseek", "litellm"}:
        raise ValueError("Unknown provider")
    if live and provider == "fixture":
        raise ValueError("--live requires a non-fixture provider")
    if provider != "fixture" and (not live or max_cases is None):
        raise ValueError("Live backtests require --live and --max-cases (fail-fast batch guard)")
    if max_cases is not None and max_cases < 1:
        raise ValueError("max_cases must be positive")
    cases = load_cases(cases_path)
    if case_slugs:
        missing = set(case_slugs) - {case["slug"] for case in cases}
        if missing:
            raise ValueError(f"Unknown case slugs: {sorted(missing)}")
        cases = [case for case in cases if case["slug"] in case_slugs]
    cases = cases[:max_cases]
    # Validate the whole batch before making any paid calls.
    for case in cases:
        if not case.get("winners") or not case.get("verified"):
            raise ValueError(f"{case['slug']}: verified winner data required; see verification_note")
        if not (REPO_ROOT / case["brief_path"]).is_file():
            raise ValueError(f"Missing brief: {case['brief_path']}")
        if live and case.get("synthetic"):
            raise ValueError("Synthetic fixtures cannot establish live winner prediction")
    if live and env_flag("HACKFORGE_USE_SENTENCE_TRANSFORMERS", default=True):
        if find_spec("sentence_transformers") is None:
            raise ValueError("Live ranking requires the existing collision extras; install hackforge[collision] before paid calls")
    results_dir = results_dir or EVALS_DIR / "baseline-results"
    bundle = read_json(FIXTURES_DIR / "dry-run-bundle.json")
    rows = []
    for case in cases:
        path = REPO_ROOT / case["brief_path"]
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            # Remove historical crowding/inferences and other run-derived data.
            parsed = read_json(path)
            text = str({key: parsed.get(key) for key in (
                "name", "theme", "tracks", "judging_criteria", "requirements", "required_tech",
                "encouraged_tech", "build_window", "deadline", "demo_requirements", "submission_artifacts",
            )})
        excludes = [str(winner[key]) for winner in case["winners"] for key in ("title", "url") if winner.get(key)]
        providers = load_providers(dry_run=provider == "fixture", fixture_bundle=bundle, provider=provider)
        with fixture_distance_mode(provider == "fixture"):
            run_dir = run_analyse(text=text, dry_run=provider == "fixture", provider=provider,
                                  fixture_bundle=bundle, live_research=False, collision_excludes=excludes,
                                  runs_root=results_dir / "_runs", visual_report=False,
                                  execution_providers=providers)
        manifest = read_json(run_dir / "run-manifest.json")
        manifest.update(source="backtest", backtest_case=case["slug"])
        write_json(run_dir / "run-manifest.json", manifest)
        ideas = total_order(run_dir)
        scores = similarity_matrix(ideas, case["winners"], scorer)
        fixture_naive = naive_baseline(text, bundle)
        fixture_scores = similarity_matrix(fixture_naive, case["winners"], scorer)
        controls = {"shuffled": shuffled_control(scores, case["winners"], threshold),
                    "naive_fixture": score_order(fixture_scores, case["winners"], threshold)}
        live_scores = fixture_scores
        naive = fixture_naive
        if live:
            # Share the run's provider: the extra call cannot reset its 40-call/$2 cap.
            naive = naive_baseline(text, bundle, provider=providers.research)
            live_scores = similarity_matrix(naive, case["winners"], scorer)
            controls["naive_live"] = score_order(live_scores, case["winners"], threshold)
        else:
            controls["naive_live"] = {**controls["naive_fixture"], "status": "fixture-only; not a live control"}
        collision_names = [analogue.get("name", "") for report in read_json(run_dir / "collision-reports.json")
                           for analogue in report.get("nearest_analogues", [])]
        rows.append({"case": case["slug"], "cutoff_class": case.get("cutoff_class", "unknown"),
                     "synthetic": case.get("synthetic", False), "run_dir": str(run_dir), "pool_size": len(ideas),
                     "ranking_ids": [idea["id"] for idea in ideas], "winner_source": case.get("winner_source"),
                     "winner_definitions": case["winners"],
                     "naive_ideas": {"fixture": fixture_naive, "live": naive if live else None},
                     "usage_including_live_naive": providers.research.usage_snapshot()
                     if hasattr(providers.research, "usage_snapshot") else None,
                     "pipeline": score_order(scores, case["winners"], threshold), "controls": controls,
                     "sensitivity": {str(floor): {
                         "pipeline": score_order(scores, case["winners"], floor),
                         "shuffled": shuffled_control(scores, case["winners"], floor),
                         "naive_fixture": score_order(fixture_scores, case["winners"], floor),
                         "naive_live": score_order(live_scores, case["winners"], floor) if live else None,
                     }
                                     for floor in sorted({max(0.0, threshold - 0.1), threshold, min(1.0, threshold + 0.1)})},
                     "leakage": {"live_research": False, "excluded": excludes,
                                 "own_winner_collision_hits": [w["title"] for w in case["winners"] if any(
                                     w["title"].casefold() in str(name).casefold() for name in collision_names)],
                                 "winner_title_reuse": [w["title"] for w in case["winners"] if any(
                                     w["title"].casefold() == str(idea.get("working_title", "")).casefold() for idea in ideas)]}})
    splits = {}
    for cutoff in ("pre-cutoff", "post-cutoff", "unknown"):
        selected = [row for row in rows if row["cutoff_class"] == cutoff and not row["synthetic"]]
        splits[cutoff] = {"count": len(selected), "pipeline_recall_at_3": sum(row["pipeline"]["recall_at_3"] for row in selected) / max(1, len(selected)),
                          "controls": {arm: sum(row["controls"][arm]["recall_at_3"] for row in selected) / max(1, len(selected))
                                       for arm in ("shuffled", "naive_fixture", "naive_live")}}
    post = splits["post-cutoff"]
    verdict = "insufficient_data"
    leakage = any(row["leakage"]["winner_title_reuse"] or row["leakage"]["own_winner_collision_hits"]
                  for row in rows if row["cutoff_class"] == "post-cutoff")
    if live and post["count"] and not leakage:
        verdict = "beats_controls" if all(post["pipeline_recall_at_3"] > value for value in post["controls"].values()) else "rework_judging_layer"
    output = results_dir / f"backtest-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    write_json(output, {"decision_rule": DECISION_RULE, "verdict": verdict, "provider": provider,
                        "scorer": scorer, "threshold": threshold, "cases": rows, "cutoff_splits": splits})
    lines = ["# Winner backtest", "", DECISION_RULE, "", f"Verdict: **{verdict}**", f"Matcher: {scorer}, threshold {threshold}",
             "", "Lexical similarity is a proxy; fixture runs do not prove winner prediction.", ""]
    for row in rows:
        lines.extend([f"## {row['case']} ({row['cutoff_class']})",
                      f"Pool: {row['pool_size']}; run: `{row['run_dir']}`",
                      "", "| Arm | Recall@3 | Recall@12 | MRR |", "|---|---:|---:|---:|"])
        for arm, metric in {"pipeline": row["pipeline"], **row["controls"]}.items():
            if metric.get("status"):
                lines.append(f"| {arm} (not run) | — | — | — |")
            else:
                lines.append(f"| {arm} | {metric['recall_at_3']:.3f} | {metric['recall_at_12']:.3f} | {metric['mrr']:.3f} |")
        lines.extend(["", "| Winner | First matching rank | Best matching rank | Similarity |",
                      "|---|---:|---:|---:|"])
        for winner in row["pipeline"]["winners"]:
            lines.append(f"| {winner['title']} | {winner['first_match_rank']} | {winner['best_match_rank']} | {winner['best_score']:.3f} |")
        lines.extend(["", f"Leakage checks: {row['leakage']}", ""])
    lines.extend(["## Cutoff splits", "", str(splits), "", "Full definitions, rankings, controls and sensitivity are in the companion JSON."])
    write_text(output.with_suffix(".md"), "\n".join(lines))
    return output
