# Production operations

## Supported deployment

HackForge 0.4 is a local-first CLI for one operator or trusted team. It stores potentially
sensitive competition materials on the machine running it; it is not a multi-tenant web
service. Python 3.9, 3.11, and 3.12 are tested.

Build and validate a release:

```bash
python -m build
twine check dist/*
python -m venv /tmp/hackforge-release
/tmp/hackforge-release/bin/pip install dist/*.whl
/tmp/hackforge-release/bin/hackforge doctor
```

## State and privacy

Installed releases default to `~/.hackforge`; source checkouts use repository-local state unless
`HACKFORGE_HOME` is explicitly set. `HACKFORGE_HOME` relocates all writable state (runs, corpus
cache, FAISS index, HackRep downloads, and evaluation outputs). Override an individual location
with `HACKFORGE_RUNS_DIR`, `HACKFORGE_INDEX_DIR`, `HACKFORGE_CORPUS_CACHE`, or
`HACKFORGE_HACKREP_DIR`. Run directories are created with mode `0700`; generated files use
`0600`.

Every analysis writes `run-status.json` and a private `run.log`. Its states are `running`, `failed`, `cancelled`,
and `complete`. Use `hackforge runs list` to find incomplete runs and `hackforge runs show
RUN_DIR` to inspect the error and last completed stage, then open `run.log` for the full traceback. A failed run is evidence;
HackForge does not silently reuse partial candidates or resume across changed prompts.

## Preflight

Run a provider-specific preflight before a trusted search. `--provider deepseek` is the default;
`--provider codex` verifies the authenticated local Codex CLI instead and does not require a
DeepSeek key. Both forms check GitHub and best-effort Devpost public search, plus the semantic
collision stack and a built FAISS index. Devpost's public search may return an AWS WAF challenge;
this is a warning when the local corpus/index is ready. Set
`HACKFORGE_REQUIRE_LIVE_DEVPOST=1` only when direct Devpost access must be a hard gate.

```bash
hackforge doctor --provider codex --strict --live
# or
hackforge doctor --provider deepseek --strict --live
```

Install `hackforge[collision]`, pull a corpus, and build its index. Trusted live runs fail
when semantic search is unavailable; they never silently switch to lexical comparison.

HackForge can use `deepseek-v4-pro` directly or your authenticated local Codex account for
private idea search. Codex child sessions are ephemeral, read-only, and ignore optional user MCP
configuration while preserving the Codex login. Competition-specific technology requirements
must come from the parsed competition brief and are not hard-coded to any named event.

Default safeguards stop a run after 40 attempted model calls, 750,000 total tokens, or a
conservative $2 estimated cost. Completed usage and pricing assumptions are recorded in
`run-manifest.json`. Adjust the `HACKFORGE_MAX_*` variables only after reviewing a fast run.
Adaptive reasoning uses `high` for research and `max` for the final pairwise decision/red-team
checks (capped at 4,096 tokens by default). Broad structured generation, collision/feasibility
reviews, and independent role votes use non-thinking decoding by default so long arrays do not
consume the run; set `HACKFORGE_DEEPSEEK_GENERATION_THINKING=1`,
`HACKFORGE_DEEPSEEK_REVIEW_THINKING=1`, or `HACKFORGE_DEEPSEEK_JUDGE_VOTE_THINKING=1` to opt in.
Collision and feasibility replies are capped at 4,096 tokens by default.
Streaming calls also enforce the configured
`HACKFORGE_STREAM_TIMEOUT` wall-clock deadline (300 seconds by default) while reasoning chunks
arrive; `HACKFORGE_LLM_TIMEOUT` remains the idle network-read timeout.

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

Balanced mode can make many model and research calls. Start with `fast` when validating
credentials or a new competition URL. Keep `run-manifest.json`, `research-sources.json`,
and the final recommendation together so evidence provenance remains intact.

## Release checklist

1. Update `src/hackforge/__init__.py`, `pyproject.toml`, and `CHANGELOG.md` together.
2. Run `ruff check src tests`, `mypy`, and `pytest -m "not slow"`.
3. Build both artifacts and run `twine check dist/*`.
4. Install the wheel into a clean virtual environment and run CLI/import smoke tests.
5. Run `hackforge doctor --strict --live`, then complete real fast and balanced runs.
6. Review dependency advisories and publish from a clean, tagged commit.

## Recovery

- `failed` at `provider_selection`: run `hackforge doctor`, then authenticate or select a provider.
- `failed` at `competition_research`: verify the public URL and ensure it does not redirect to a private network.
- `failed` at `hard_gates`: inspect `gate-results.json`; the system intentionally returns no unsupported finalist.
- `failed` at collision/feasibility: inspect repair mutations in `search-lineage.json`.
- `cancelled`: start a new run. Partial output is retained for diagnosis but never treated as complete.
