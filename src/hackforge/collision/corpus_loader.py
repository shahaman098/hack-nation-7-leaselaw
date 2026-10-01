from __future__ import annotations

from pathlib import Path
from typing import Any

from hackforge.models import CandidateIdea, CollisionReport
from hackforge.paths import CORPORA_DIR, RUNS_DIR
from hackforge.utils import read_json


def load_candidates(run_dir: Path) -> list[CandidateIdea]:
    """Load candidate ideas from a completed HackForge run directory."""
    for name in ("raw-concepts.json", "finalists.json", "clustered-concepts.json"):
        path = run_dir / name
        if not path.exists():
            continue
        payload = read_json(path)
        rows: list[Any]
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = payload.get("ideas") or payload.get("candidates") or payload.get("clusters") or []
        else:
            continue
        ideas: list[CandidateIdea] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                ideas.append(CandidateIdea.model_validate(row))
            except Exception:
                continue
        if ideas:
            return ideas
    return []


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
