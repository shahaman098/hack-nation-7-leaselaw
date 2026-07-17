from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hackforge.paths import EVALS_DIR, FIXTURES_DIR, REPO_ROOT
from hackforge.pipeline import run_analyse
from hackforge.providers import DryRunProvider
from hackforge.utils import read_json, write_json, write_text


def naive_baseline(brief_text: str, fixture_bundle: dict[str, Any]) -> list[str]:
    provider = DryRunProvider(fixture_bundle)
    resp = provider.complete(
        "You are a hackathon idea generator.",
        f"Here is the hackathon description. Give me ten winning ideas.\n\n{brief_text}",
    )
    data = resp.text
    try:
        parsed = json.loads(data)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except json.JSONDecodeError:
        pass
    return [line.strip("- ").strip() for line in data.splitlines() if line.strip()][:10]


def _archetype_tags(text: str) -> set[str]:
    tags: set[str] = set()
    blob = text.lower()
    mapping = {
        "tutor": "tutor",
        "mental": "wellness",
        "resume": "resume",
        "summar": "summariser",
        "carbon": "carbon-dashboard",
        "navigat": "navigator",
        "crisis": "crisis-navigator",
        "outreach": "outreach-agent",
        "meeting note": "meeting-notes",
        "chatbot": "chatbot",
        "dashboard": "dashboard",
    }
    for needle, tag in mapping.items():
        if needle in blob:
            tags.add(tag)
    return tags


def score_arm(ideas: list[Any], blacklist: dict[str, Any]) -> dict[str, Any]:
    if ideas and isinstance(ideas[0], dict):
        texts = [
            " ".join(
                str(i.get(k, ""))
                for k in ("working_title", "primary_user", "imported_mechanism", "last_mile_action")
            )
            for i in ideas
        ]
        named_data = sum(1 for i in ideas if i.get("data_sources"))
        users = {str(i.get("primary_user") or "") for i in ideas if i.get("primary_user")}
        mechanisms = {str(i.get("mechanism_family") or i.get("imported_mechanism") or "") for i in ideas}
        actions = {str(i.get("last_mile_action") or "") for i in ideas if i.get("last_mile_action")}
        demos = {str(i.get("demo_type") or i.get("killer_demo") or "") for i in ideas}
    else:
        texts = [str(i) for i in ideas]
        named_data = 0
        users, mechanisms, actions, demos = set(), set(), set(), set()

    tags: set[str] = set()
    for t in texts:
        tags |= _archetype_tags(t)
    crowded_needles = [
        "tutor",
        "mental-health",
        "mental health",
        "wellness",
        "resume",
        "summaris",
        "summariz",
        "carbon-footprint",
        "carbon footprint",
        "chatbot",
        "meeting notes",
        "opportunity board",
        "eligibility navigator",
        "crisis navigator",
        "campaign fatigue",
    ]
    crowded_hits = sum(1 for t in texts if any(n in t.lower() for n in crowded_needles))

    return {
        "count": len(texts),
        "archetype_tag_set": sorted(tags),
        "archetype_diversity": len(tags),
        "crowded_keyword_hits": crowded_hits,
        "named_data_source_ideas": named_data,
        "unsupported_claim_proxy": sum(1 for t in texts if "ai" in t.lower() and "data" not in t.lower()),
        "semantic_duplicate_rate": _duplicate_rate(texts),
        "coverage": {
            "users": len(users),
            "mechanisms": len(mechanisms),
            "actions": len(actions),
            "demos": len(demos),
        },
    }


def _duplicate_rate(texts: list[str]) -> float:
    if len(texts) < 2:
        return 0.0
    duplicate_pairs = 0
    pairs = 0
    token_sets = [{token for token in text.lower().split() if len(token) > 3} for text in texts]
    for index, left in enumerate(token_sets):
        for right in token_sets[index + 1 :]:
            pairs += 1
            similarity = len(left & right) / max(1, len(left | right))
            duplicate_pairs += int(similarity >= 0.82)
    return duplicate_pairs / pairs


def run_benchmark(benchmark_dir: Path, *, dry_run: bool = True) -> Path:
    del dry_run  # always uses dry fixtures for reproducibility in v1
    blacklist = read_json(REPO_ROOT / "corpora" / "crowded-archetypes" / "default.json")
    fixture_bundle = read_json(FIXTURES_DIR / "dry-run-bundle.json")
    results_dir = EVALS_DIR / "baseline-results"
    results_dir.mkdir(parents=True, exist_ok=True)

    cases = sorted(benchmark_dir.glob("*.md")) if benchmark_dir.exists() else []
    if not cases:
        cases = [FIXTURES_DIR / "sample-hackathon.md"]

    report_rows: list[dict[str, Any]] = []
    for case in cases:
        text = case.read_text(encoding="utf-8")
        baseline_ideas = naive_baseline(text, fixture_bundle)
        baseline_scores = score_arm(baseline_ideas, blacklist)

        run_dir = run_analyse(
            input_path=case,
            dry_run=True,
            fixture_bundle=fixture_bundle,
            seeds_per_lane=5,
            runs_root=results_dir / "_runs",
        )
        raw = read_json(run_dir / "raw-concepts.json")
        pipeline_scores = score_arm(raw, blacklist)
        manifest = read_json(run_dir / "run-manifest.json")
        final_ids = set(manifest.get("final_output_ids") or [])
        finalists = [idea for idea in raw if idea.get("id") in final_ids]
        collisions = read_json(run_dir / "collision-reports.json")
        collision_by = {report.get("candidate_id"): report for report in collisions}
        finalist_evidence = all(idea.get("evidence_ids") for idea in finalists) and bool(finalists)
        differentiated = all(
            collision_by.get(idea.get("id"), {}).get("differentiator_is_substantive", False)
            for idea in finalists
        )

        report_rows.append(
            {
                "case": case.name,
                "baseline": {"ideas": baseline_ideas, "metrics": baseline_scores},
                "pipeline": {
                    "run_dir": str(run_dir),
                    "metrics": pipeline_scores,
                    "primary": manifest.get("final_primary_id"),
                },
                "comparison": {
                    "pipeline_more_diverse_tags": pipeline_scores["archetype_diversity"]
                    >= baseline_scores["archetype_diversity"],
                    "pipeline_fewer_crowded_hits": pipeline_scores["crowded_keyword_hits"]
                    <= baseline_scores["crowded_keyword_hits"],
                    "pipeline_more_named_data": pipeline_scores["named_data_source_ideas"]
                    >= baseline_scores["named_data_source_ideas"],
                    "lower_semantic_duplicate_rate": pipeline_scores["semantic_duplicate_rate"]
                    < baseline_scores["semantic_duplicate_rate"],
                    "broad_dimension_coverage": all(
                        pipeline_scores["coverage"][dimension] >= 3
                        for dimension in ("users", "mechanisms", "actions", "demos")
                    ),
                    "every_finalist_has_cited_evidence": finalist_evidence,
                    "no_banned_structural_archetypes": pipeline_scores["crowded_keyword_hits"] == 0,
                    "finalists_differ_from_nearest_analogue": differentiated,
                },
            }
        )

    out = results_dir / "latest-benchmark.json"
    write_json(out, {"cases": report_rows})
    md_lines = ["# Baseline vs pipeline benchmark", ""]
    for row in report_rows:
        md_lines.append(f"## {row['case']}")
        md_lines.append(f"- Baseline crowded hits: {row['baseline']['metrics']['crowded_keyword_hits']}")
        md_lines.append(f"- Pipeline crowded hits: {row['pipeline']['metrics']['crowded_keyword_hits']}")
        md_lines.append(f"- Pipeline named data ideas: {row['pipeline']['metrics']['named_data_source_ideas']}")
        md_lines.append(f"- Pipeline semantic duplicate rate: {row['pipeline']['metrics']['semantic_duplicate_rate']:.3f}")
        md_lines.append(f"- Pipeline dimension coverage: {row['pipeline']['metrics']['coverage']}")
        md_lines.append(f"- Comparison flags: {row['comparison']}")
        md_lines.append("")
    write_text(results_dir / "latest-benchmark.md", "\n".join(md_lines))
    return out
