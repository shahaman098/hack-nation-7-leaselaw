from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich import print

from hackforge import __version__
from hackforge.collision import audit_collisions_engine, collision_markdown
from hackforge.collision.corpus_loader import load_candidates
from hackforge.diagnostics import doctor_ready_for_live, run_doctor
from hackforge.evals import run_benchmark
from hackforge.evals.backtest import load_cases, run_backtest
from hackforge.evals.promptfoo_runner import run_promptfoo
from hackforge.integrations.corpus_pull import build_index_from_cache as build_corpus_index
from hackforge.integrations.corpus_pull import pull_sources as pull_corpora
from hackforge.memory import append_human_override, learn_from_runs, list_runs
from hackforge.paths import EVALS_DIR
from hackforge.pipeline import run_analyse
from hackforge.providers import load_providers
from hackforge.research import search_devpost_projects
from hackforge.utils import env_flag, read_json, write_json, write_text


@click.group()
@click.version_option(version=__version__, prog_name="hackforge")
def main() -> None:
    """HackForge: private competition strategy, research, and collision laboratory."""


@main.command()
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, path_type=Path),
    help="Local competition brief/file. Can be combined with --url and --text.",
)
@click.option(
    "--url",
    type=str,
    help="Public competition page URL. Can be combined with --text/--input.",
)
@click.option(
    "--text",
    type=str,
    help="Paste competition description inline, or pass '-' to read from stdin.",
)
@click.option("--team-size", type=str)
@click.option("--deadline", type=str)
@click.option("--skills", type=str)
@click.option("--dry-run", is_flag=True, default=False, help="Run the deterministic fixture provider.")
@click.option(
    "--fixture-bundle",
    type=click.Path(exists=True, path_type=Path),
    help="Deterministic fixture bundle used only with --dry-run.",
)
@click.option(
    "--provider",
    type=click.Choice(["deepseek", "codex", "litellm"]),
    default="deepseek",
    show_default=True,
    help="Internal HackForge execution backend; independent from entry technology requirements.",
)
@click.option(
    "--search-profile",
    type=click.Choice(["fast", "balanced", "exhaustive"]),
    default="balanced",
    show_default=True,
)
@click.option("--finalists", type=click.IntRange(3, 8), default=3, show_default=True)
@click.option("--output-root", type=click.Path(file_okay=False, path_type=Path))
@click.option("--no-visual-report", is_flag=True, default=False)
@click.option(
    "--live-research/--no-live-research",
    default=None,
    help="Enable/disable optional public-project research enrichment (auto-enabled for live providers).",
)
def analyse(
    input_path: Path | None,
    url: str | None,
    text: str | None,
    team_size: str | None,
    deadline: str | None,
    skills: str | None,
    dry_run: bool,
    fixture_bundle: Path | None,
    provider: str,
    search_profile: str,
    finalists: int,
    output_root: Path | None,
    no_visual_report: bool,
    live_research: bool | None,
) -> None:
    """Run evidence → idea search → collision → feasibility → blind judging.

    Pass any combination of --url, --text, and --input. Pasted text and local
    files are treated as authoritative operator evidence; URLs add official pages.
    """
    if not any([input_path, url, text]):
        raise click.UsageError("Provide --input, --url, and/or --text (they can be combined)")
    if text == "-":
        text = sys.stdin.read()
        if not text.strip():
            raise click.UsageError("Read '--text -' from stdin, but received empty input")
    fixture = read_json(fixture_bundle) if fixture_bundle else None
    if fixture is not None and not dry_run:
        raise click.UsageError("--fixture-bundle is only allowed with --dry-run")
    run_dir = run_analyse(
        input_path=input_path,
        url=url,
        text=text,
        team_size=team_size,
        deadline=deadline,
        skills=skills,
        dry_run=dry_run,
        fixture_bundle=fixture,
        runs_root=output_root,
        live_research=live_research,
        provider=provider,
        search_profile=search_profile,
        finalists=finalists,
        visual_report=not no_visual_report,
    )
    print(f"[bold green]HackForge complete:[/bold green] {run_dir}")


@main.command()
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--live", "live_enrich", is_flag=True, default=False, help="Add live Devpost enrichment.")
@click.option("--llm", "use_llm", is_flag=True, default=False, help="Use an LLM for collision adjudication.")
@click.option("--limit", type=click.IntRange(1, 100), default=20, show_default=True)
def collide(run_dir: Path, live_enrich: bool, use_llm: bool, limit: int) -> None:
    """Run collision audit against an existing HackForge run."""
    candidates = load_candidates(run_dir)[:limit]
    if not candidates:
        raise click.ClickException("No candidate ideas found in run directory")
    provider = None
    if use_llm:
        bundle = load_providers(dry_run=False, provider="deepseek")
        provider = bundle.collision
    reports = audit_collisions_engine(
        provider,
        candidates,
        live_enrich=live_enrich,
        use_llm=use_llm,
        require_semantic=env_flag("HACKFORGE_REQUIRE_SEMANTIC_COLLISION", default=False),
    )
    write_json(run_dir / "collision-reports.json", [report.model_dump() for report in reports])
    write_text(run_dir / "collision-analysis.md", collision_markdown(reports))
    print(f"[green]Wrote {len(reports)} collision reports to {run_dir}[/green]")


@main.group()
def corpus() -> None:
    """Manage optional public-project corpora and semantic collision index."""


@corpus.command("pull")
@click.option(
    "--source",
    type=click.Choice(["local", "twango", "alpha", "alvanlii", "hackrep", "all"]),
    default="local",
    show_default=True,
)
@click.option("--limit", type=click.IntRange(1, 100_000), default=5000, show_default=True)
def corpus_pull(source: str, limit: int) -> None:
    """Download/normalize optional public competition-project corpora."""
    results = pull_corpora([source], limit=limit)
    for src, path in results.items():
        print(f"[green]{src}[/green]: {path}")


@corpus.command("build-index")
@click.option("--model", type=str, default=None, help="SentenceTransformer model override.")
@click.option("--max-records", type=click.IntRange(1, 250_000), default=None)
def corpus_build_index(model: str | None, max_records: int | None) -> None:
    """Build FAISS index from normalized optional project corpora."""
    del model  # EmbedIndex owns its default model; retained for CLI compatibility.
    result = build_corpus_index(max_records=max_records)
    print(f"[bold green]Index built[/bold green]: {result}")


@main.group()
def research() -> None:
    """Optional public Devpost research helpers."""


@research.command("winners")
@click.argument("hackathon_slug")
@click.option("--limit", type=click.IntRange(1, 100), default=40, show_default=True)
def research_winners(hackathon_slug: str, limit: int) -> None:
    """Search public Devpost projects for a Devpost hackathon/event slug."""
    from hackforge.integrations.devpost_live import get_winners

    rows = get_winners(hackathon_slug, max_results=limit)
    print(json.dumps(rows, indent=2))


@research.command("exists")
@click.argument("query")
@click.option("--limit", type=click.IntRange(1, 50), default=10, show_default=True)
def research_exists(query: str, limit: int) -> None:
    """Search public Devpost projects for a concept description."""
    rows = search_devpost_projects(query, max_results=limit)
    print(json.dumps([source.model_dump() for source in rows], indent=2))


@main.group("eval", invoke_without_command=True)
@click.option("--provider", type=click.Choice(["fixture", "deepseek", "litellm"]), default="fixture")
@click.option("--promptfoo/--no-promptfoo", default=True)
@click.pass_context
def eval_command(ctx: click.Context, provider: str, promptfoo: bool) -> None:
    """Run baseline competition benchmarks and optional Promptfoo evaluation."""
    if ctx.invoked_subcommand:
        return
    dry_run = provider == "fixture"
    results_path = run_benchmark(EVALS_DIR / "benchmarks", dry_run=dry_run)
    print(f"[green]Baseline benchmark:[/green] {results_path}")
    if promptfoo:
        promptfoo_result = run_promptfoo(dry_run=dry_run)
        print(f"[green]Promptfoo:[/green] {promptfoo_result}")


@eval_command.command("backtest")
@click.option("--cases", type=click.Path(exists=True, path_type=Path), default=EVALS_DIR / "backtest" / "cases.json")
@click.option("--provider", type=click.Choice(["fixture", "deepseek", "codex", "litellm"]), default="fixture")
@click.option("--live", is_flag=True, help="Explicitly authorize live calls.")
@click.option("--max-cases", type=click.IntRange(1))
@click.option("--scorer", type=click.Choice(["token", "embed"]), default="token")
@click.option("--threshold", type=click.FloatRange(0, 1), default=0.30)
@click.option("--case", "case_slugs", multiple=True, help="Select a case slug (repeatable).")
def eval_backtest(cases: Path, provider: str, live: bool, max_cases: int | None, scorer: str, threshold: float,
                  case_slugs: tuple[str, ...]) -> None:
    """Score rankings against verified winners; all three controls are included."""
    try:
        selected = [case for case in load_cases(cases) if not case_slugs or case["slug"] in case_slugs]
        count = min(len(selected), max_cases or len(selected))
        if provider != "fixture":
            print(f"Live estimate: {count} full runs plus {count} naive calls. DeepSeek caps: 40 calls/$2 per run; Codex has no accounting.")
        output = run_backtest(cases, provider=provider, live=live, max_cases=max_cases, scorer=scorer,
                              threshold=threshold, case_slugs=case_slugs)
    except (ValueError, RuntimeError) as exc:
        raise click.ClickException(str(exc)) from exc
    print(f"[green]Backtest:[/green] {output}")


@main.command()
@click.option(
    "--provider",
    type=click.Choice(["deepseek", "codex", "litellm"]),
    default="deepseek",
    show_default=True,
)
@click.option("--strict", is_flag=True, default=False, help="Exit non-zero when required selected capabilities fail.")
@click.option("--live", "live_probe", is_flag=True, default=False, help="Probe selected backend and optional enrichments.")
def doctor(provider: str, strict: bool, live_probe: bool) -> None:
    """Check selected runtime, resources, and optional integrations."""
    checks = run_doctor(live_probe=live_probe, provider=provider)
    for check in checks:
        if check.ok:
            prefix = "[green]OK[/green]"
        elif check.level == "warn":
            prefix = "[yellow]WARN[/yellow]"
        else:
            prefix = "[red]FAIL[/red]"
        print(f"{prefix} [bold]{check.name}[/bold]: {check.detail}")
        if check.hint and not check.ok:
            print(f"      [yellow]{check.hint}[/yellow]")
    if strict and not doctor_ready_for_live(checks):
        raise click.ClickException("Required environment checks failed")


@main.group()
def runs() -> None:
    """Inspect and learn from private HackForge runs."""


@runs.command("list")
@click.option("--root", type=click.Path(file_okay=False, path_type=Path))
def runs_list(root: Path | None) -> None:
    rows = list_runs(root)
    if not rows:
        print("[yellow]No runs found.[/yellow]")
        return
    for row in rows:
        print(
            f"{row['created_at'] or '-'}  [bold]{row['run']}[/bold]  "
            f"competition={row['competition']} raw={row['raw']} finalists={row['finalists']} "
            f"primary={row['primary'] or '-'} result={row['result'] or '-'} status={row['status']}"
        )


@runs.command("show")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def runs_show(run_dir: Path) -> None:
    manifest_path = run_dir / "run-manifest.json"
    status_path = run_dir / "run-status.json"
    if not manifest_path.exists() and not status_path.exists():
        raise click.ClickException("No run-manifest.json or run-status.json found")
    payload: dict[str, object] = {}
    if status_path.exists():
        payload["status"] = read_json(status_path)
    if manifest_path.exists():
        payload["manifest"] = read_json(manifest_path)
    print(json.dumps(payload, indent=2))


@runs.command("learn")
@click.option("--root", type=click.Path(file_okay=False, path_type=Path))
def runs_learn(root: Path | None) -> None:
    print(json.dumps(learn_from_runs(root), indent=2))


@main.command("record-outcome")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--result", required=True, type=click.Choice(["winner", "finalist", "dnq"]))
@click.option("--note", default="", help="Optional post-competition note.")
def record_outcome(run_dir: Path, result: str, note: str) -> None:
    """Attach the real competition outcome to a run for experimental memory."""
    manifest_path = run_dir / "run-manifest.json"
    if not manifest_path.exists():
        raise click.ClickException("run-manifest.json not found")
    manifest = read_json(manifest_path)
    manifest["competition_result"] = result
    if note:
        manifest.setdefault("outcome_notes", []).append(note)
    write_json(manifest_path, manifest)
    print(f"[green]Recorded competition result '{result}' for {run_dir.name}[/green]")


@main.command("override")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--from-id", "from_id", required=True)
@click.option("--to-id", "to_id", required=True)
@click.option("--reason", required=True)
def override(run_dir: Path, from_id: str, to_id: str, reason: str) -> None:
    """Record a human selection override without erasing model outputs."""
    data = append_human_override(
        run_dir,
        {
            "type": "selection_override",
            "from_id": from_id,
            "to_id": to_id,
            "reason": reason,
        },
    )
    print(f"[green]Override recorded. Total overrides: {len(data['human_overrides'])}[/green]")


if __name__ == "__main__":
    main()
