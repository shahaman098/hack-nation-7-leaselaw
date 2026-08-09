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
    competition_result: str | None = None,
    hackathon_result: str | None = None,
) -> dict[str, Any]:
    """Build a run manifest.

    `hackathon_result` remains an input alias for 0.4 callers. New manifests write
    `competition_result`; readers continue to accept the legacy key in old runs.
    """
    result = competition_result or hackathon_result
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
        "competition_result": result,
        "notes": "Update competition_result and human_overrides after the competition.",
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


def _load_manifest(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "run-manifest.json"
    if not path.exists():
        return None
    try:
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _load_status(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "run-status.json"
    if not path.exists():
        return None
    try:
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _manifest_result(manifest: dict[str, Any]) -> Any:
    """Read 0.5 competition outcome first, then the 0.4 legacy field."""
    return manifest.get("competition_result") or manifest.get("hackathon_result")


def list_runs(runs_root: Path | None = None) -> list[dict[str, Any]]:
    """Return one summary row per run directory, newest first."""
    from hackforge.paths import RUNS_DIR

    root = runs_root or RUNS_DIR
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for run_dir in sorted(root.iterdir()):
        if not run_dir.is_dir():
            continue
        manifest = _load_manifest(run_dir)
        status = _load_status(run_dir)
        if manifest is None and status is None:
            continue
        manifest = manifest or {}
        status = status or {}
        counts = manifest.get("candidate_counts", {})
        total_time = sum(float(value) for value in manifest.get("stage_timings_seconds", {}).values())
        rows.append(
            {
                "run": run_dir.name,
                "path": str(run_dir),
                "competition": manifest.get("competition_name", run_dir.name),
                "created_at": manifest.get("created_at", status.get("created_at", "")),
                "dry_run": manifest.get("dry_run", False),
                "raw": counts.get("raw", 0),
                "finalists": counts.get("finalists", 0),
                "primary": manifest.get("final_primary_id"),
                "result": _manifest_result(manifest),
                "seconds": round(total_time, 2),
                "status": status.get("status", "complete" if manifest else "unknown"),
                "stage": status.get("stage", ""),
                "error": status.get("error", ""),
            }
        )
    rows.sort(key=lambda row: row["created_at"], reverse=True)
    return rows


def learn_from_runs(runs_root: Path | None = None) -> dict[str, Any]:
    """Aggregate experimental memory across runs for continuous improvement."""
    from hackforge.paths import RUNS_DIR

    root = runs_root or RUNS_DIR
    rows: list[dict[str, Any]] = []
    provider_stats: dict[str, dict[str, float]] = {}
    outcome_stats: dict[str, int] = {}
    prompt_versions_seen: dict[str, int] = {}

    if root.exists():
        for run_dir in sorted(root.iterdir()):
            if not run_dir.is_dir():
                continue
            manifest = _load_manifest(run_dir)
            if manifest is None:
                continue
            rows.append(manifest)
            counts = manifest.get("candidate_counts", {})
            raw = float(counts.get("raw", 0) or 0)
            finalists = float(counts.get("finalists", 0) or 0)
            research_provider = (manifest.get("providers") or {}).get("research", "unknown")
            stat = provider_stats.setdefault(
                research_provider,
                {"runs": 0, "raw": 0, "finalists": 0},
            )
            stat["runs"] += 1
            stat["raw"] += raw
            stat["finalists"] += finalists
            result = _manifest_result(manifest)
            if result:
                outcome_stats[str(result)] = outcome_stats.get(str(result), 0) + 1
            for prompt_version in (manifest.get("prompt_versions") or {}):
                prompt_versions_seen[prompt_version] = prompt_versions_seen.get(prompt_version, 0) + 1

    for stat in provider_stats.values():
        stat["survival_rate"] = (
            round(stat["finalists"] / stat["raw"], 4) if stat["raw"] else 0.0
        )

    recorded = [manifest for manifest in rows if _manifest_result(manifest)]
    recommendations: list[str] = []
    if not rows:
        recommendations.append("No runs found yet. Run `hackforge analyse` to start building memory.")
    if rows and not recorded:
        recommendations.append(
            "No outcomes recorded. Use `hackforge record-outcome <run> --result winner|finalist|dnq` "
            "so HackForge can learn which configurations perform best."
        )
    if provider_stats:
        best = max(provider_stats.items(), key=lambda item: item[1]["survival_rate"])
        recommendations.append(
            f"Highest finalist survival rate: '{best[0]}' ({best[1]['survival_rate']:.1%} of raw ideas)."
        )

    return {
        "total_runs": len(rows),
        "runs_with_outcomes": len(recorded),
        "provider_stats": provider_stats,
        "outcome_counts": outcome_stats,
        "prompt_versions_seen": prompt_versions_seen,
        "recommendations": recommendations,
    }
