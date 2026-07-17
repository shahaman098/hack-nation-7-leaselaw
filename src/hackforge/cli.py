from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from hackforge import __version__
from hackforge.paths import REPO_ROOT
from hackforge.pipeline import run_analyse
from hackforge.utils import env_flag, read_json, write_json, write_text

console = Console()


@click.group()
@click.version_option(__version__, prog_name="hackforge")
def main() -> None:
    """HackForge — hackathon research & collision laboratory."""


@main.command("analyse")
@click.argument("input_file", required=False, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--url", "url", default=None, help="Fetch competition page URL.")
@click.option(
    "--provider",
    "provider_name",
    type=click.Choice(["deepseek", "codex", "litellm"]),
    default="deepseek",
    show_default=True,
    help="Model backend; DeepSeek is fail-closed and never falls back to Codex or another model.",
)
@click.option(
    "--search-profile",
    type=click.Choice(["fast", "balanced", "exhaustive"]),
    default="balanced",
    show_default=True,
)
@click.option("--finalists", default=3, show_default=True, type=click.IntRange(min=3))
@click.option("--visual-report/--no-visual-report", default=True, show_default=True)
@click.option(
    "--output-root",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Directory for private run artifacts (defaults to HACKFORGE_RUNS_DIR).",
)
@click.option(
    "--live-research/--no-live-research",
    default=None,
    help="Control public-project enrichment (automatic for live runs).",
)
@click.option("--team-size", default=None, help="Team size constraint.")
@click.option("--deadline", default=None, help="Deadline constraint.")
@click.option("--skills", default=None, help="Available skills / infrastructure.")
@click.option("--seeds-per-lane", default=8, show_default=True, type=int)
def analyse_cmd(
    input_file: Optional[Path],
    url: Optional[str],
    provider_name: str,
    search_profile: str,
    finalists: int,
    visual_report: bool,
    output_root: Optional[Path],
    live_research: Optional[bool],
    team_size: Optional[str],
    deadline: Optional[str],
    skills: Optional[str],
    seeds_per_lane: int,
) -> None:
    """Run research → ideation → collision → judge pipeline."""
    if not input_file and not url:
        raise click.UsageError("Provide INPUT_FILE or --url")

    console.print(
        f"[bold]HackForge[/bold] starting {search_profile} search… "
        "[dim](progress is checkpointed to run-status.json)[/dim]"
    )
    try:
        run_dir = run_analyse(
            input_path=input_file,
            url=url,
            dry_run=False,
            team_size=team_size,
            deadline=deadline,
            skills=skills,
            seeds_per_lane=seeds_per_lane,
            live_research=(
                live_research
                if live_research is not None
                else (True if env_flag("HACKFORGE_LIVE_RESEARCH") else None)
            ),
            provider=provider_name,
            search_profile=search_profile,
            finalists=finalists,
            visual_report=visual_report,
            runs_root=output_root,
        )
    except (RuntimeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    console.print(f"[green]Run complete:[/green] {run_dir}")
    console.print(f"  - {run_dir / 'final-recommendation.md'}")
    console.print(f"  - {run_dir / 'run-manifest.json'}")
    if visual_report:
        console.print(f"  - {run_dir / 'idea-landscape.html'}")


@main.group("corpus")
def corpus_group() -> None:
    """Pull Devpost corpora and build FAISS collision indexes."""


@corpus_group.command("pull")
@click.option(
    "--source",
    "sources",
    multiple=True,
    default=("local",),
    help="alpha | twango | alvanlii | hackrep | local | all (repeatable)",
)
@click.option("--limit", default=5000, show_default=True, type=int)
@click.option("--winners-only", is_flag=True, help="Alpha: prefer winners when available.")
def corpus_pull_cmd(sources: tuple[str, ...], limit: int, winners_only: bool) -> None:
    """Download/normalize HF corpora into corpora/cache (not committed)."""
    from hackforge.integrations.corpus_pull import pull_sources

    srcs = list(sources)
    console.print(f"Pulling sources: {', '.join(srcs)} …")
    results = pull_sources(srcs, limit=limit, winners_only=winners_only)
    for k, v in results.items():
        console.print(f"  [green]{k}[/green] → {v}")


@corpus_group.command("build-index")
@click.option("--max-records", default=None, type=int, help="Cap records for faster builds.")
def corpus_build_index_cmd(max_records: Optional[int]) -> None:
    """Build FAISS index from corpora/cache + local analogues."""
    from hackforge.integrations.corpus_pull import build_index_from_cache

    console.print("Building FAISS index…")
    path = build_index_from_cache(max_records=max_records)
    console.print(f"[green]Index ready:[/green] {path}")


@main.command("collide")
@click.argument("target", type=click.Path(exists=True, path_type=Path))
@click.option("--live", "live_enrich", is_flag=True, help="Query Devpost/Product Hunt.")
@click.option("--llm", "use_llm", is_flag=True, help="Run LLM auditor (needs API keys).")
def collide_cmd(target: Path, live_enrich: bool, use_llm: bool) -> None:
    """Collision-audit concepts from a run dir or raw-concepts.json."""
    from hackforge.collision.engine import run_collide_on_ideas
    from hackforge.models import CandidateIdea
    from hackforge.providers import load_providers

    if target.is_dir():
        concepts_path = target / "raw-concepts.json"
        out_md = target / "collision-analysis.md"
        out_json = target / "collision-reports.json"
    else:
        concepts_path = target
        out_md = target.with_suffix(".collision.md")
        out_json = target.with_suffix(".collision.json")

    raw = read_json(concepts_path)
    ideas = [CandidateIdea(**row) for row in raw]
    provider = None
    if use_llm:
        bundle = load_providers()
        provider = bundle.collision

    reports, md = run_collide_on_ideas(
        ideas,
        provider,
        live_enrich=live_enrich,
        use_llm=use_llm,
    )
    write_text(out_md, md)
    write_json(out_json, [r.model_dump() for r in reports])
    console.print(f"[green]Collision report:[/green] {out_md}")
    high = sum(1 for r in reports if r.collision_risk == "high")
    console.print(f"  candidates={len(reports)} high_risk={high}")


@main.group("research")
def research_group() -> None:
    """Live Devpost / optional Product Hunt / Apify research."""


@research_group.command("winners")
@click.argument("slug")
@click.option("--limit", default=40, type=int)
def research_winners_cmd(slug: str, limit: int) -> None:
    from hackforge.integrations.devpost_live import get_winners

    rows = get_winners(slug, max_results=limit)
    console.print_json(json.dumps(rows, indent=2))


@research_group.command("exists")
@click.argument("idea_text")
@click.option("--limit", default=10, type=int)
def research_exists_cmd(idea_text: str, limit: int) -> None:
    from hackforge.integrations.devpost_live import check_idea_exists

    rows = check_idea_exists(idea_text, max_results=limit)
    console.print_json(json.dumps(rows, indent=2))


@research_group.command("apify-gallery")
@click.argument("hackathon_url")
def research_apify_cmd(hackathon_url: str) -> None:
    from hackforge.integrations.apify_bootstrap import pull_gallery

    rows = pull_gallery(hackathon_url)
    if not rows:
        console.print("[yellow]No results (set APIFY_TOKEN or check actor).[/yellow]")
        return
    console.print_json(json.dumps(rows[:20], indent=2))


@main.command("eval")
@click.option("--dry-run", is_flag=True, help="Write Promptfoo config; skip npx if needed.")
@click.option("--skip-benchmark", is_flag=True)
def eval_cmd(dry_run: bool, skip_benchmark: bool) -> None:
    """Run Promptfoo config + existing baseline-vs-pipeline benchmark."""
    from hackforge.evals.promptfoo_runner import run_promptfoo

    pf = run_promptfoo(dry_run=dry_run)
    console.print(f"Promptfoo: {pf.get('status')} — {pf.get('config')}")
    if pf.get("hint"):
        console.print(f"  hint: {pf['hint']}")
    if not skip_benchmark:
        from hackforge.evals.benchmark import run_benchmark

        out = run_benchmark(REPO_ROOT / "evals" / "benchmark-hackathons", dry_run=True)
        console.print(f"[green]Benchmark:[/green] {out}")


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

    manifest_path = run_dir / "run-manifest.json"
    data = read_json(manifest_path)
    data["hackathon_result"] = result
    write_json(manifest_path, data)
    append_human_override(run_dir, {"type": "hackathon_result", "result": result, "note": note})
    console.print(f"[green]Updated[/green] {manifest_path}")


@main.command("doctor")
@click.option("--strict", is_flag=True, help="Exit non-zero when live-run requirements are not met.")
@click.option(
    "--provider",
    "provider_name",
    type=click.Choice(["deepseek", "codex", "litellm"]),
    default="deepseek",
    show_default=True,
    help="Validate the backend you plan to use for analysis.",
)
@click.option("--live", "live_probe", is_flag=True, help="Probe the selected provider plus public research services.")
def doctor_cmd(strict: bool, provider_name: str, live_probe: bool) -> None:
    """Verify environment, selected provider, corpus, and optional integrations."""
    from rich.markup import escape
    from rich.table import Table

    from hackforge.diagnostics import doctor_ready_for_live, run_doctor

    checks = run_doctor(live_probe=live_probe, provider=provider_name)
    table = Table(title="HackForge doctor", show_lines=False)
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Detail")
    for c in checks:
        if c.ok:
            status = "[green]OK[/green]"
        elif c.level == "warn":
            status = "[yellow]WARN[/yellow]"
        else:
            status = "[red]FAIL[/red]"
        detail = c.detail
        if c.hint and not c.ok:
            detail += f"\n[dim]{escape(c.hint)}[/dim]"
        table.add_row(c.name, status, detail)
    console.print(table)

    if doctor_ready_for_live(checks):
        console.print("[green]Ready for live runs.[/green]")
    else:
        console.print(
            "[yellow]Not fully configured for live runs.[/yellow] "
            "Address FAIL rows before analysis."
        )
        if strict:
            raise click.ClickException("Live-run preflight failed")


@main.group("runs")
def runs_group() -> None:
    """Inspect and learn from past runs (experimental memory)."""


@runs_group.command("list")
def runs_list_cmd() -> None:
    """List past runs newest-first with key stats."""
    from rich.table import Table

    from hackforge.memory import list_runs

    rows = list_runs()
    if not rows:
        console.print("[yellow]No runs yet.[/yellow] Try `hackforge analyse competition.md --provider deepseek`.")
        return
    table = Table(title=f"{len(rows)} run(s)")
    for col in ("run", "status", "competition", "raw", "finalists", "result", "seconds", "dry_run"):
        table.add_column(col)
    for r in rows:
        table.add_row(
            r["run"],
            str(r["status"]),
            str(r["competition"])[:32],
            str(r["raw"]),
            str(r["finalists"]),
            str(r["result"] or "-"),
            str(r["seconds"]),
            "yes" if r["dry_run"] else "no",
        )
    console.print(table)


@runs_group.command("show")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def runs_show_cmd(run_dir: Path) -> None:
    """Print a run's manifest as JSON."""
    manifest = run_dir / "run-manifest.json"
    if not manifest.exists():
        status = run_dir / "run-status.json"
        if status.exists():
            console.print_json(json.dumps(read_json(status), indent=2))
            return
        raise click.ClickException(f"No run-manifest.json or run-status.json in {run_dir}")
    console.print_json(json.dumps(read_json(manifest), indent=2))


@runs_group.command("learn")
def runs_learn_cmd() -> None:
    """Aggregate memory across runs: provider survival rates, outcomes, next steps."""
    from hackforge.memory import learn_from_runs

    report = learn_from_runs()
    console.print_json(json.dumps(report, indent=2))
    for rec in report.get("recommendations", []):
        console.print(f"[cyan]•[/cyan] {rec}")


if __name__ == "__main__":
    main()
