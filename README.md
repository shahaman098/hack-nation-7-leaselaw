# Hackathon Idea Search

**AI agents: start at [`AGENTS.md`](AGENTS.md)** · ops [`docs/OPS_RUNBOOK.md`](docs/OPS_RUNBOOK.md) · Claude [`CLAUDE.md`](CLAUDE.md) · Gemini [`GEMINI.md`](GEMINI.md) · live board [`docs/WIN_BOARD.md`](docs/WIN_BOARD.md) · snapshot [`docs/STATUS.md`](docs/STATUS.md).

## Two things in this repo

| | |
|--|--|
| **LeaseLaw (active HN7 entry)** | `apps/leaselaw/` — Track 02 RealPage housing-law navigator |
| **HackForge** | Idea search/ranking engine — `src/hackforge/`, `briefs/`, `runs/` |

Hack-Nation playbook/CV: `hack-nation/`.

### LeaseLaw quick start

```bash
cd apps/leaselaw
pip install -r requirements.txt
python -m src.export_outputs
python -m src.eval_harness    # expect 5/5
uvicorn src.main:app --port 8012
```

---

# HackForge

**A private local search engine for evidence-backed, competition-winning strategies and concepts — not the submitted entry itself.**

HackForge is competition-agnostic. It can analyse a hackathon, data challenge, robotics or hardware contest, research challenge, startup/pitch competition, grant, bounty, accelerator selection process, innovation challenge, or another structured competition as long as you provide its rules/brief.

The engine derives constraints from the current competition instead of assuming a particular provider, model, platform, sponsor, dataset, track, team size, build duration, demo format, or submission artifact.

Private decision system for:

- Competition intelligence and structured requirement extraction
- Required vs encouraged technology separation
- Competition-specific crowding maps and novelty research
- Cross-domain opportunity × mechanism ideation
- Sparse quality-diversity search and directed mutation
- Optional public-project / semantic collision evidence
- Independent feasibility review against the actual constraints
- Blind multi-role judging using the actual official criteria and weights/priorities
- Experimental memory across runs
- One recommended winner plus two structurally different backups

## Competition-agnostic contract

A parsed `CompetitionBrief` can express, independently:

- official tracks (or no tracks)
- sponsors (or no sponsors)
- build window and/or submission deadline
- team constraints
- mandatory technologies/platforms
- encouraged technologies that must **not** become mandatory
- data requirements and provided/available datasets
- required submission artifacts (repo, model, deck, report, video, prototype, form, etc.)
- demo/prototype/presentation requirements
- eligibility and other structured requirements
- judging criteria with percentages, numeric weights, or qualitative priorities

Absent requirements become `not_applicable`; they do not silently become failures. Participant eligibility is captured as competition intelligence but is not treated as a property of an idea.

Candidate concepts use generic `technology_roles` and `requirement_satisfaction` maps. HackForge's own LLM backend is separate from the technology a submitted entry must use.

## Quick start (Codex-first, no UI)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Authenticate once in the Codex app or terminal. No API key is needed.
codex login

# Verify the selected backend. Optional research/collision integrations warn by default.
hackforge doctor --provider codex --strict --live

# Analyse any public competition page.
hackforge analyse --url https://competition.example/ --provider codex --search-profile fast

# Or paste a description (works alone, or combined with a URL/file).
hackforge analyse --text "48h civic hackathon..." --provider codex --search-profile fast
hackforge analyse --url https://competition.example/ --text "Extra rules the page missed..." --provider codex
```

`--url`, `--text`, and `--input` can be combined. Pasted/file text is authoritative operator evidence; the URL adds official pages. Use `--text -` to read a long paste from stdin.

If you prefer the API-backed default, copy `.env.example` to `.env`, set `DEEPSEEK_API_KEY`, then replace `--provider codex` with `--provider deepseek`. DeepSeek failures stop the run; no provider or model fallback is attempted.

## Optional collision/research enrichment

Public repositories, Devpost projects, and the bundled FAISS/Devpost-style corpus are **enrichment**, not universal prerequisites. This matters for competitions with sparse public code, private domains, physical prototypes, grants, pitches, research, or hardware.

```bash
# Optional semantic/public-project stack
pip install -e ".[dev,collision]"
hackforge corpus pull --source local
hackforge corpus build-index

# Optional larger public corpora
hackforge corpus pull --source twango --limit 1000
hackforge corpus build-index --max-records 1000

# Collision-only on an existing run
hackforge collide runs/<slug>/
hackforge collide runs/<slug>/ --live --llm
```

Make an enrichment source blocking only when your workflow specifically requires it:

```bash
export HACKFORGE_REQUIRE_GITHUB_RESEARCH=1
export HACKFORGE_REQUIRE_LIVE_DEVPOST=1
export HACKFORGE_REQUIRE_SEMANTIC_COLLISION=1
```

`HACKFORGE_MIN_GITHUB_RESULTS` and `HACKFORGE_MIN_DEVPOST_RESULTS` can set explicit minimum result counts in strict workflows. Without the corresponding strict flag, zero public matches is valid.

## Generated artifacts

Source checkouts write to `runs/`; installed wheels write private state to `~/.hackforge/runs/`. Override this with `--output-root`, `HACKFORGE_RUNS_DIR`, or `HACKFORGE_HOME`.

Every search writes artifacts including:

- `competition-brief.json`
- `research-sources.json`
- `verified-research.md`
- `opportunity-cards.json`
- `mechanism-cards.json`
- `raw-concepts.json`
- `gate-results.json`
- `idea-archive.json`
- `search-lineage.json`
- `collision-reports.json`
- `feasibility-reports.json`
- `blind-judge-results.json`
- `build-plan.json` and `build-plan.md` (unless `--no-build-plan`)
- `final-recommendation.md`
- `idea-landscape.html` (unless disabled)
- `run-manifest.json`
- `run-status.json`
- `run.log`

Balanced search evaluates 48 concepts: 32 initial crosses plus 16 directed mutations over two rounds, collision-audits 12, judges up to 6, and returns 3 outputs.

The build-plan stage follows red-team selection and plans the **final primary**,
including any backup swap. It adds one bounded, schema-validated call through the
existing feasibility provider; existing DeepSeek budgets still apply. Use
`--no-build-plan` to save that call and omit both plan artifacts. The manifest
records the flag, stage timing and optional-stage call budget.

Plans contain architecture, dependency-ordered tasks with acceptance tests, demo
steps, scope cuts, and submission checks. They embed the original feasibility
report unchanged rather than regenerating delivery risk or estimates. If the
brief has no `build_window`, the plan is **unscheduled** with null task time slots;
a submission deadline alone never becomes an invented build timebox.

### Winner backtests

```bash
# Offline two-case integration check; not evidence of winner prediction
hackforge eval backtest --cases evals/backtest/fixtures/cases.json
# Explicit, bounded live smoke; includes one additional naive-control call
hackforge eval backtest --provider codex --live --max-cases 1 --case openai-build-week
```

Reports (`backtest-*.json` and `.md`) go to `evals/baseline-results/`; private run
artifacts stay in its ignored `_runs/`, outside `runs learn`. The harness disables
live research and removes the case's own winner titles/URLs from collision
retrieval, including repair paths. All three controls use the same matcher.
DeepSeek's existing call/cost caps include the live-naive call; Codex has no cost
accounting, so live batches require `--max-cases` and fail fast.

The five real cases and verification status are in `evals/backtest/cases.json`.
Unverified winner lists block execution; unknown model cutoffs are reported
separately and cannot establish post-cutoff performance. The frozen decision rule
is in [`evals/backtest/protocol.md`](evals/backtest/protocol.md). Build-plan
implementation was explicitly authorized despite the inconclusive backtest;
that does not establish winner prediction. Backtests disable build planning so
their inference budget remains the ranking run plus one live-naive call.

## Requirement-driven gates

The deterministic gate layer is derived from the current brief:

- `evidence_backed` — ideas must remain traceable to verified competition/evidence sources
- `required_technology_fit` — applies only when technology/platform use is mandatory
- `requirement_compliance` — applies to structured mandatory concept/submission requirements
- `data_viability` — applies when the competition or concept actually depends on data; provided/local/sensor/user-supplied/fixture data is allowed with a credible access plan
- `delivery_feasible` — applies when a build window, deadline, or team constraint is known
- `demo_fit` — applies only when a demo/prototype/pitch/presentation/working proof is required or explicitly judged
- `specific_track_fit` — applies only when official tracks exist

Eligibility rules are reported separately rather than used to score the idea itself.

## Judging

Blind judging receives the competition's actual criteria and constraints. Pairwise selection does not import a universal technical, sponsor, demo, impact, or design tie-breaker. Parsed percentages/numeric weights are used when available; qualitative priorities such as high/medium/low are converted into relative weights.

The judge panel surfaces disagreement rather than automatically averaging it away.

## Experimental memory

Every run writes a `run-manifest.json` containing prompt versions, provider models, timings, rejections, finalists, and outcome metadata. Close the loop after a competition:

```bash
hackforge record-outcome runs/<slug>/ --result winner --note "Won target category"
hackforge runs learn
```

## Reliability

- LLM calls retry with exponential backoff and honor configured timeouts.
- Runs stop at configurable call, token, and estimated-cost budgets; usage is written to the manifest.
- Structured model output is schema-validated; malformed live outputs do not become silent mock replacements.
- Required competition rules are fail-closed; absent rules are not invented.
- Public GitHub/Devpost research failures are recorded and non-blocking by default.
- Semantic collision uses FAISS automatically when available and becomes mandatory only with `HACKFORGE_REQUIRE_SEMANTIC_COLLISION=1`.
- Competition crawling blocks local/private/reserved networks, credential-bearing URLs, and oversized responses.
- Public project text is untrusted collision evidence and is never executed as instructions.
- Generated run artifacts use private file permissions and durable lifecycle checkpoints.

## Providers

`--provider deepseek|codex|litellm` selects HackForge's internal execution backend explicitly.

- `deepseek` calls the configured official DeepSeek API directly.
- `codex` runs authenticated, ephemeral, read-only `codex exec` sessions and can use your existing Codex login without an OpenAI API key.
- `litellm` is available for explicitly configured supported providers.

This backend selection has **no relationship** to what technology the competition entry is required to use. Mandatory entry technologies come only from the parsed competition brief.

Default per-run safeguards are 40 model calls, 750,000 total tokens, and a conservative $2 estimated-cost ceiling. Adjust `HACKFORGE_MAX_LLM_CALLS`, `HACKFORGE_MAX_TOTAL_TOKENS`, or `HACKFORGE_MAX_COST_USD` deliberately for broader searches.

## Development

```bash
make install-all
make lint
make typecheck
make test-fast
```

CI runs ruff, mypy, and the fixture-backed test suite on Python 3.9/3.11/3.12. It also builds the sdist/wheel, validates metadata, installs the wheel into a clean environment, and runs package/resource smoke tests.

## Pipeline

1. Crawl/read the official competition material as untrusted evidence.
2. Extract facts, judging criteria, required/encouraged tech, time/team/data/artifact/demo constraints, eligibility, and competition-specific crowding.
3. Generate opportunity cards and mechanism cards independently.
4. Cross them into concepts suitable for the permitted competition format (software, hardware, research, analysis, physical prototype, pitch, process/service design, etc.).
5. Populate a sparse quality-diversity archive.
6. Mutate toward empty regions and repair applicable gate/collision failures.
7. Apply only the gates that the current brief makes relevant.
8. Add optional public/semantic collision evidence and independent feasibility review.
9. Blind-judge finalists against the actual official criteria and constraints.
10. Return one winner plus structurally different backups, with a decision dossier and machine-readable provenance.

The retrieve → generate → deduplicate → rank → novelty-filter structure is informed by [AI-Researcher](https://github.com/NoviScl/AI-Researcher); reflective mutation is informed by [GEPA](https://github.com/CerebrasResearch/gepa); the native sparse archive follows the MAP-Elites pattern documented by [pyribs](https://github.com/icaros-usc/pyribs). HackForge does not add these projects as runtime dependencies and no source code was copied.

## Docs

- [`docs/finalist-evaluation-handbook.md`](docs/finalist-evaluation-handbook.md)
- [`docs/deferred-ui.md`](docs/deferred-ui.md)
- [`docs/production-operations.md`](docs/production-operations.md)
- [`SECURITY.md`](SECURITY.md)

## License

[MIT](LICENSE).
