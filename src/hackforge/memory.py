from __future__ import annotations

from pathlib import Path
from typing import Any

from hackforge import __version__
from hackforge.utils import corpora_version, prompt_fingerprint, utc_now_iso, write_json


def build_run_manifest(
    *,
    run_dir: Path,
    competition_name: str,
    dry_run: bool,
    providers: dict[str, Any],
    input_sources: list[str],
    input_hash: str,
    stage_timings: dict[str, float],
    candidate_counts: dict[str, int],
    rejections: list[dict[str, str]],
    human_overrides: list[dict[str, Any]] | None = None,
    final_primary_id: str | None = None,
    final_backup_id: str | None = None,
    hackathon_result: str | None = None,
) -> dict[str, Any]:
    manifest = {
        "hackforge_version": __version__,
        "created_at": utc_now_iso(),
        "run_dir": str(run_dir),
        "competition_name": competition_name,
        "dry_run": dry_run,
        "prompt_versions": prompt_fingerprint(),
        "corpora_version": corpora_version(),
        "providers": providers,
        "input_sources": input_sources,
        "input_hash": input_hash,
        "stage_timings_seconds": stage_timings,
        "candidate_counts": candidate_counts,
        "rejections": rejections,
        "judgments_path": "blind-judge-results.json",
        "human_overrides": human_overrides or [],
        "final_primary_id": final_primary_id,
        "final_backup_id": final_backup_id,
        "hackathon_result": hackathon_result,
        "notes": "Update hackathon_result and human_overrides after the competition.",
    }
    write_json(run_dir / "run-manifest.json", manifest)
    return manifest


def append_human_override(run_dir: Path, override: dict[str, Any]) -> dict[str, Any]:
    path = run_dir / "run-manifest.json"
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("human_overrides", []).append({**override, "at": utc_now_iso()})
    write_json(path, data)
    return data
