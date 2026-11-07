# Production operations

## Supported deployment

HackForge is a local-first competition strategy CLI for one operator or a trusted team. It stores potentially sensitive competition materials on the machine running it; it is not a multi-tenant web service. Python 3.9, 3.11, and 3.12 are tested.

HackForge's internal LLM provider is independent from the technology required by an entry. Competition requirements are parsed from the current brief and may describe software, hardware, data, science, research, a physical prototype, a pitch, a grant submission, or another allowed format.

Build and validate a release:

```bash
python -m build
twine check dist/*
python -m venv /tmp/hackforge-release
/tmp/hackforge-release/bin/pip install dist/*.whl
/tmp/hackforge-release/bin/hackforge doctor
```

## State and privacy

Installed releases default to `~/.hackforge`; source checkouts use repository-local state unless `HACKFORGE_HOME` is explicitly set. `HACKFORGE_HOME` relocates all writable state (runs, corpus cache, FAISS index, HackRep downloads, and evaluation outputs). Override an individual location with `HACKFORGE_RUNS_DIR`, `HACKFORGE_INDEX_DIR`, `HACKFORGE_CORPUS_CACHE`, or `HACKFORGE_HACKREP_DIR`.

Every analysis writes `run-status.json` and a private `run.log`. States are `running`, `failed`, `cancelled`, and `complete`. Use `hackforge runs list` to find incomplete runs and `hackforge runs show RUN_DIR` to inspect the last completed stage and error. Failed partial output remains diagnostic evidence and is never silently treated as a completed recommendation.

## Preflight

Run a provider-specific preflight before a trusted search:

```bash
hackforge doctor --provider codex --strict --live
# or
hackforge doctor --provider deepseek --strict --live
```

`--strict` means required capabilities for the selected configuration must pass. By default, that means the selected LLM runtime and core package resources. Public GitHub research, Devpost discovery, FAISS, and a local semantic corpus are optional enrichment and therefore appear as warnings when unavailable.

Make a particular enrichment source mandatory only when your workflow needs it:

```bash
export HACKFORGE_REQUIRE_GITHUB_RESEARCH=1
export HACKFORGE_REQUIRE_LIVE_DEVPOST=1
export HACKFORGE_REQUIRE_SEMANTIC_COLLISION=1
```

When strict GitHub/Devpost modes are enabled, `HACKFORGE_MIN_GITHUB_RESULTS` and `HACKFORGE_MIN_DEVPOST_RESULTS` can define explicit minimum result counts. Without the strict flags, zero public matches is valid. This allows sparse/private/non-software competitions to run without inventing a public-code requirement.

Semantic collision search uses a built FAISS index automatically when available. In default mode it is enrichment, not a prerequisite. Enable `HACKFORGE_REQUIRE_SEMANTIC_COLLISION=1` only when the relevant comparison corpus has enough coverage to justify fail-closed semantic novelty checks.

## Competition requirements

Research should distinguish:

- mandatory technologies/platforms from encouraged tools;
- build window from submission deadline;
- concept/submission requirements from participant eligibility;
- required data from merely available datasets;
- required demos/prototypes/pitches from optional presentation polish;
- official tracks from an open-format competition;
- required submission artifacts from suggested materials.

Absent constraints are represented as absent and become `not_applicable` in candidate gating. Do not fill missing rules with conventions from another event.

## Recommended live invocation

```bash
# Codex-first local workflow
hackforge analyse \
  --url https://competition.example/ \
  --provider codex \
  --search-profile fast \
  --finalists 3 \
  --output-root /private/hackforge-runs

# DeepSeek API workflow
hackforge analyse \
  --url https://competition.example/ \
  --provider deepseek \
  --search-profile balanced \
  --finalists 3 \
  --output-root /private/hackforge-runs
```

You can also supply a local brief or inline text when a competition page is inaccessible. Keep `competition-brief.json`, `research-sources.json`, `gate-results.json`, and the final recommendation together so requirement/evidence provenance remains inspectable.

## Operational safeguards

Default safeguards stop a run after 40 attempted model calls, 750,000 total tokens, or the configured estimated-cost ceiling. Usage and pricing assumptions are recorded in `run-manifest.json`.

- LLM structured outputs are schema-validated.
- Applicable competition requirements are fail-closed; absent requirements are not invented.
- Public enrichment failures are preserved as provenance without blocking default runs.
- Collision and feasibility kills remain visible in generated reports.
- Competition crawling blocks local/private/reserved networks and credential-bearing URLs.
- Public project text is untrusted evidence and is never executed as instructions.

## Release checklist

1. Update `src/hackforge/__init__.py`, `pyproject.toml`, and `CHANGELOG.md` together when changing the released version.
2. Run `ruff check src tests`, `mypy`, and `pytest -m "not slow"`.
3. Build both artifacts and run `twine check dist/*`.
4. Install the wheel into a clean virtual environment and run CLI/import/resource smoke tests.
5. Run `hackforge doctor --strict --live` for each provider configuration you intend to support.
6. Exercise representative competition formats, including at least one trackless/no-required-tech brief and one strict-technology/data brief.
7. Review dependency advisories and publish from a clean tagged commit.

## Recovery

- `failed` at `provider_selection`: run `hackforge doctor`, then authenticate or select a ready provider.
- `failed` at `competition_research`: inspect the official source, anti-bot response, or malformed structured output.
- `failed` at `hard_gates`: inspect `gate-results.json`; only applicable competition requirements should be blocking.
- `failed` at collision/feasibility: inspect `collision-reports.json`, `feasibility-reports.json`, and repair mutations in `search-lineage.json`.
- strict public-research failure: disable the relevant strict flag unless that source is genuinely mandatory for your process.
- `cancelled`: start a new run; partial output is retained for diagnosis but never treated as complete.
