from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from hackforge import __version__
from hackforge.paths import FIXTURES_DIR, REPO_ROOT
from hackforge.pipeline import run_analyse
from hackforge.utils import env_flag, read_json

console = Console()


@click.group()
@click.version_option(__version__, prog_name="hackforge")
def main() -> None:
    """HackForge — hackathon research & idea-selection laboratory."""


@main.command("analyse")
@click.argument("input_file", required=False, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--url", "url", default=None, help="Fetch competition page URL.")
@click.option("--dry-run", is_flag=True, help="Use fixture LLM responses (no API keys).")
@click.option("--team-size", default=None, help="Team size constraint.")
@click.option("--deadline", default=None, help="Deadline constraint.")
@click.option("--skills", default=None, help="Available skills / infrastructure.")
@click.option("--seeds-per-lane", default=8, show_default=True, type=int)
@click.option(
    "--fixture-bundle",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="JSON fixture responses for dry-run.",
)
def analyse_cmd(
    input_file: Optional[Path],
    url: Optional[str],
    dry_run: bool,
    team_size: Optional[str],
    deadline: Optional[str],
    skills: Optional[str],
    seeds_per_lane: int,
    fixture_bundle: Optional[Path],
) -> None:
    """Run the full research → ideation → collision → judge pipeline."""
    if not input_file and not url:
        raise click.UsageError("Provide INPUT_FILE or --url")

    dry = dry_run or env_flag("HACKFORGE_DRY_RUN")
    bundle = None
    if dry:
        default_fixture = FIXTURES_DIR / "dry-run-bundle.json"
        path = fixture_bundle or default_fixture
        if path.exists():
            bundle = read_json(path)
        else:
            console.print("[yellow]No fixture bundle found; dry-run provider will use stubs.[/yellow]")

    console.print("[bold]HackForge[/bold] starting analyse…")
    run_dir = run_analyse(
        input_path=input_file,
        url=url,
        dry_run=dry,
        fixture_bundle=bundle,
        team_size=team_size,
        deadline=deadline,
        skills=skills,
        seeds_per_lane=seeds_per_lane if not dry else min(seeds_per_lane, 5),
    )
    console.print(f"[green]Run complete:[/green] {run_dir}")
    console.print(f"  - {run_dir / 'final-recommendation.md'}")
    console.print(f"  - {run_dir / 'run-manifest.json'}")


@main.command("benchmark")
@click.argument(
    "benchmark_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    required=False,
)
@click.option("--dry-run", is_flag=True, default=True, help="Default dry-run for reproducibility.")
def benchmark_cmd(benchmark_dir: Optional[Path], dry_run: bool) -> None:
    """Compare naïve ten-ideas baseline vs full pipeline on fixture hackathons."""
    from hackforge.evals.benchmark import run_benchmark

    root = benchmark_dir or (REPO_ROOT / "evals" / "benchmark-hackathons")
    out = run_benchmark(root, dry_run=dry_run)
    console.print(f"[green]Benchmark written:[/green] {out}")


@main.command("record-outcome")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--result", required=True, help="e.g. winner / finalist / participated / dnq")
@click.option("--note", default="", help="Optional human note.")
def record_outcome_cmd(run_dir: Path, result: str, note: str) -> None:
    """Attach competition outcome to an existing run-manifest (experimental memory)."""
    from hackforge.memory import append_human_override
    from hackforge.utils import read_json, write_json

    manifest_path = run_dir / "run-manifest.json"
    data = read_json(manifest_path)
    data["hackathon_result"] = result
    write_json(manifest_path, data)
    append_human_override(run_dir, {"type": "hackathon_result", "result": result, "note": note})
    console.print(f"[green]Updated[/green] {manifest_path}")


if __name__ == "__main__":
    main()
