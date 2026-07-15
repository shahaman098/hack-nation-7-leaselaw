from __future__ import annotations

from pathlib import Path
from typing import Any

from hackforge.models import Analogue, CandidateIdea, CollisionReport, SimilarityDims
from hackforge.paths import CORPORA_DIR, RUNS_DIR
from hackforge.providers import LLMProvider
from hackforge.utils import load_prompt, read_json


def load_analogue_corpus() -> list[dict[str, Any]]:
    analogues: list[dict[str, Any]] = []
    for sub in ("past-winners", "finalists", "sponsor-showcases", "crowded-archetypes"):
        root = CORPORA_DIR / sub
        if not root.exists():
            continue
        for path in root.glob("**/*"):
            if path.suffix.lower() == ".json":
                data = read_json(path)
                if isinstance(data, list):
                    analogues.extend(data)
                elif isinstance(data, dict):
                    if "high_collision" in data:
                        for label in data.get("high_collision", []):
                            analogues.append(
                                {
                                    "name": label,
                                    "source": f"corpora/{sub}",
                                    "user": "generic",
                                    "problem": label,
                                    "mechanism": "crowded-archetype",
                                    "data": "",
                                    "action": "",
                                    "demo": "",
                                }
                            )
                    else:
                        analogues.append(data)
    # Prior runs' selected concepts
    if RUNS_DIR.exists():
        for manifest in RUNS_DIR.glob("*/clustered-concepts.json"):
            try:
                clustered = read_json(manifest)
                for c in clustered.get("clusters", []) if isinstance(clustered, dict) else []:
                    analogues.append(
                        {
                            "name": c.get("representative_id", "prior-run"),
                            "source": f"prior-run:{manifest.parent.name}",
                            "mechanism": c.get("imported_mechanism", ""),
                            "user": c.get("primary_user", ""),
                            "action": c.get("last_mile_action", ""),
                        }
                    )
            except Exception:
                continue
    return analogues


def audit_collisions(
    provider: LLMProvider,
    candidates: list[CandidateIdea],
    corpus: list[dict[str, Any]] | None = None,
) -> list[CollisionReport]:
    corpus = corpus if corpus is not None else load_analogue_corpus()
    template, _ = load_prompt("collision-audit")
    payload = {
        "candidates": [c.model_dump() for c in candidates],
        "analogue_corpus_sample": corpus[:80],
    }
    raw = provider.complete_json(template, str(payload))
    items = raw if isinstance(raw, list) else raw.get("reports") or []
    reports: list[CollisionReport] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        reports.append(_parse_report(item))

    # Heuristic fallback if LLM returned nothing useful
    covered = {r.candidate_id for r in reports}
    for c in candidates:
        if c.id not in covered:
            reports.append(_heuristic_report(c, corpus))
    return reports


def _parse_report(item: dict[str, Any]) -> CollisionReport:
    analogues = []
    for a in item.get("nearest_analogues") or []:
        if not isinstance(a, dict):
            continue
        sim = a.get("similarities") or {}
        analogues.append(
            Analogue(
                name=str(a.get("name") or "unknown"),
                source=str(a.get("source") or ""),
                url=str(a.get("url") or ""),
                similarities=SimilarityDims(
                    same_user=bool(sim.get("same_user")),
                    same_problem=bool(sim.get("same_problem")),
                    same_mechanism=bool(sim.get("same_mechanism")),
                    same_data=bool(sim.get("same_data")),
                    same_action=bool(sim.get("same_action")),
                    same_demo=bool(sim.get("same_demo")),
                ),
                differences=list(a.get("differences") or []),
            )
        )
    return CollisionReport(
        candidate_id=str(item.get("candidate_id") or ""),
        nearest_analogues=analogues,
        collision_risk=item.get("collision_risk") or "medium",
        observable_differentiator=str(item.get("observable_differentiator") or ""),
        differentiator_is_substantive=bool(item.get("differentiator_is_substantive")),
        kill_recommendation=bool(item.get("kill_recommendation")),
        notes=str(item.get("notes") or ""),
    )


def _heuristic_report(candidate: CandidateIdea, corpus: list[dict[str, Any]]) -> CollisionReport:
    hits = []
    blob = " ".join(
        [
            candidate.primary_user,
            candidate.painful_workflow,
            candidate.imported_mechanism,
            candidate.last_mile_action,
        ]
    ).lower()
    for a in corpus:
        name = str(a.get("name") or a.get("problem") or "")
        target = " ".join(str(a.get(k, "")) for k in ("name", "problem", "mechanism", "action")).lower()
        overlap = sum(1 for tok in blob.split() if len(tok) > 4 and tok in target)
        if overlap >= 3 or (name and name.lower() in blob):
            hits.append(
                Analogue(
                    name=name or "corpus-hit",
                    source=str(a.get("source") or "corpus"),
                    similarities=SimilarityDims(same_problem=True, same_mechanism=overlap >= 4),
                    differences=["heuristic match only"],
                )
            )
    risk = "high" if len(hits) >= 3 else "medium" if hits else "low"
    return CollisionReport(
        candidate_id=candidate.id,
        nearest_analogues=hits[:3],
        collision_risk=risk,  # type: ignore[arg-type]
        observable_differentiator=candidate.hard_to_fake_advantage or candidate.killer_demo,
        differentiator_is_substantive=bool(candidate.hard_to_fake_advantage),
        kill_recommendation=risk == "high" and not candidate.hard_to_fake_advantage,
        notes="heuristic corpus overlap",
    )


def collision_markdown(reports: list[CollisionReport]) -> str:
    lines = ["# Collision analysis", ""]
    for r in reports:
        lines.append(f"## {r.candidate_id}")
        lines.append(f"- Risk: **{r.collision_risk}**")
        lines.append(f"- Kill?: {r.kill_recommendation}")
        lines.append(f"- Differentiator: {r.observable_differentiator}")
        lines.append(f"- Substantive?: {r.differentiator_is_substantive}")
        for a in r.nearest_analogues:
            sim = a.similarities
            lines.append(
                f"  - Analogue `{a.name}` ({a.source}): "
                f"user={sim.same_user} problem={sim.same_problem} mechanism={sim.same_mechanism} "
                f"data={sim.same_data} action={sim.same_action} demo={sim.same_demo}"
            )
        lines.append("")
    return "\n".join(lines)
