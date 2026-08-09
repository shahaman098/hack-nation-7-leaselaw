# HackForge

**A private local search engine for evidence-backed, competition-winning ideas — not the submitted product.**

Private decision system for:

- Competition intelligence and crowding blacklists
- Isolated cross-domain ideation lanes
- **FAISS + Devpost corpus collision detection**
- Independent feasibility review
- Blind multi-role judging with disagreement surfaced
- Experimental memory across runs
- Opportunity × mechanism crossing, sparse quality-diversity search, and directed mutation
- One recommended winner plus two structurally different backups

## Quick start (Codex-first, no UI)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,collision]"   # source checkout

# Authenticate once in the Codex app or terminal. No API key is needed.
codex login

# Build the local FAISS collision corpus/index.
hackforge corpus pull --source local
hackforge corpus build-index

# Verify the exact backend you will use, then run the private CLI workflow.
hackforge doctor --provider codex --strict --live
hackforge analyse --url https://competition.example/ --provider codex --search-profile fast

# Add a larger public Devpost corpus when you want stronger novelty coverage.
hackforge corpus pull --source twango --limit 1000
hackforge corpus build-index --max-records 1000

# Use --no-visual-report to skip the optional self-contained HTML landscape.
# All evidence and run artifacts remain local to your machine.
```

If you prefer the API-backed default, copy `.env.example` to `.env`, set
`DEEPSEEK_API_KEY`, then replace `--provider codex` with `--provider deepseek`.
DeepSeek failures stop the run; no provider or model fallback is attempted.

```bash
# Optional large HF pulls (Alpha-Hack / twango / alvanlii / HackRep metadata)
hackforge corpus pull --source all --limit 5000
hackforge corpus build-index

# Collision-only on an existing run
hackforge collide runs/<slug>/ 
hackforge collide runs/<slug>/ --live --llm
```

Source checkouts write to `runs/`; installed wheels write private state to
`~/.hackforge/runs/`. Override this with `--output-root`, `HACKFORGE_RUNS_DIR`, or
`HACKFORGE_HOME`. In addition to the legacy research,
collision, feasibility, judge, and recommendation files, every search writes:

- `research-sources.json`
- `opportunity-cards.json`
- `mechanism-cards.json`
- `idea-archive.json`
- `search-lineage.json`
- `idea-landscape.html`
- `run-status.json` (durable running/failed/cancelled/complete lifecycle state)
- `run.log` (private stage log and full traceback when a run fails)

Balanced search evaluates 48 concepts: 32 initial crosses plus 16 directed mutations
over two rounds, collision-audits 12, judges 6, and returns 3.

## Collision product surface

| Command | Purpose |
|---------|---------|
| `hackforge corpus pull` | Normalize HF Devpost corpora into `corpora/cache/` |
| `hackforge corpus build-index` | FAISS index under `corpora/indexes/` |
| `hackforge collide` | Dimensional + FAISS (+ optional live) audit |
| `hackforge research winners \| exists` | Live Devpost (Python client) |
| `hackforge eval` | Promptfoo config + baseline benchmark |
| `hackforge doctor` | Verify keys, corpora, and optional integrations |
| `hackforge runs list \| show \| learn` | Inspect experimental memory across runs |
| `hackforge record-outcome` | Attach competition result to a run manifest |

**Hard rule:** Alpha-Hack is used as **corpus fuel only**. Its strategy generator is not wired into ideation.

## Experimental memory

Every run writes a `run-manifest.json` (prompt versions, provider models, timings, rejections, finalists). Close the loop after a competition and let HackForge learn which configurations win:

```bash
hackforge record-outcome runs/<slug>/ --result winner --note "Won sponsor track"
hackforge runs learn   # provider survival rates + recommendations
```

## Reliability

- LLM calls retry with exponential backoff (via `tenacity`) and honor `HACKFORGE_LLM_TIMEOUT`.
- Runs stop at configurable call, token, and estimated-cost budgets; usage is written to the manifest.
- Ideation lanes run concurrently (`HACKFORGE_IDEATION_WORKERS`, default 4); any failed lane fails the run and is recorded in `run.log`.
- `complete_json` re-prompts up to twice when a model returns non-JSON.
- Live analysis is fail-closed: provider, schema, missing-row, feasibility, collision, and judging failures never produce mock replacement data.
- Live analysis requires verified GitHub evidence and a working semantic corpus/index. Devpost live
  search is attempted and its failures are recorded, but AWS WAF failures do not stop a run by
  default because the downloaded Devpost corpus provides the mandatory collision evidence. Set
  `HACKFORGE_REQUIRE_LIVE_DEVPOST=1` when direct live Devpost access must be enforced.
- Semantic collision search and the configured embedding model are mandatory by default; failures are logged instead of silently downgraded.
- Artifacts use atomic writes, private file permissions, and durable stage checkpoints.
- Competition crawling blocks local/private/reserved networks, credential-bearing URLs, and responses over 2 MB.
- Public project text is untrusted collision evidence and is never executed as instructions.

## Development

```bash
make install-all   # editable install with all extras + dev tools
make lint          # ruff
make typecheck     # mypy
make test-fast     # tests without model/network downloads
```

CI (GitHub Actions) runs ruff, mypy, and the fixture-backed test suite on Python 3.9/3.11/3.12.
It also builds the sdist/wheel, validates metadata, installs the wheel into a clean
environment, and runs an installed-package analysis smoke test.

## Providers

`--provider deepseek|codex|litellm` selects live execution explicitly. DeepSeek is the
default and calls the official API directly. `codex` runs authenticated, ephemeral,
read-only `codex exec` sessions with stage JSON schemas, using the account's supported
default model unless `HACKFORGE_CODEX_MODEL` is explicitly set. Its child sessions ignore
your optional Codex MCP configuration but retain your Codex login, which keeps this private
workflow independent of unrelated MCP connectivity. Run `hackforge doctor --provider codex
--strict --live` before selecting it. Fixture providers are
restricted to tests and benchmarks and are not exposed by `hackforge analyse`.

Set `DEEPSEEK_API_KEY`; `HACKFORGE_DEEPSEEK_MODEL` defaults to `deepseek-v4-pro`.
`HACKFORGE_DEEPSEEK_REASONING=adaptive` uses `high` effort for evidence extraction and `max`
for the final pairwise decision and red-team stages (capped at 4,096 tokens by default). Broad
opportunity, mechanism, concept, mutation, collision, feasibility, and independent role-vote
stages use constrained non-thinking decoding by default so a large structured response does not
monopolise the run; set `HACKFORGE_DEEPSEEK_GENERATION_THINKING=1`,
`HACKFORGE_DEEPSEEK_REVIEW_THINKING=1`, or `HACKFORGE_DEEPSEEK_JUDGE_VOTE_THINKING=1` to opt in.
Collision and feasibility replies are capped at 4,096 tokens by default.
Streaming calls also honor the configured
`HACKFORGE_STREAM_TIMEOUT` wall-clock deadline (300 seconds by default) even while reasoning
chunks arrive. The default path never reads
OpenAI/Anthropic keys and never substitutes another provider or model after a failure.

HackForge's model is independent from technology required by a competition. Competition-specific
technology requirements are taken from the parsed brief rather than being hard-coded to a named event.

Default per-run safeguards are 40 model calls, 750,000 total tokens, and a conservative
$2 estimated-cost ceiling. Set `HACKFORGE_MAX_LLM_CALLS`, `HACKFORGE_MAX_TOTAL_TOKENS`,
or `HACKFORGE_MAX_COST_USD` deliberately when a broader search needs more capacity.

## Promptfoo (optional Node)

```bash
brew install node   # once
hackforge eval      # writes evals/promptfoo/ and runs npx promptfoo when available
```

## Langfuse (optional)

```bash
docker compose -f docker-compose.langfuse.yml up -d
# set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST
```

## Pipeline

1. Crawl official pages and retrieve public-project collision evidence
2. Separate verified facts, inference, unresolved claims, and crowding
3. Generate opportunity cards and product-free mechanism cards independently
4. Cross cards into lane-constrained concepts
5. Populate a native sparse quality-diversity archive
6. Mutate toward empty regions and collision failures
7. Apply fail-closed evidence, data, technology, solo-scope, and demo gates
8. FAISS + dimension-level collision audit and independent feasibility review
9. Randomized blind judging, direct pairwise comparison, and diversity-constrained outputs
10. Decision dossier, machine artifacts, manifest, and self-contained landscape

The retrieve → generate → deduplicate → rank → novelty-filter structure is informed by
[AI-Researcher](https://github.com/NoviScl/AI-Researcher); reflective mutation is informed
by [GEPA](https://github.com/CerebrasResearch/gepa); the native sparse archive follows the
MAP-Elites pattern documented by [pyribs](https://github.com/icaros-usc/pyribs). HackForge
does not add these projects as runtime dependencies and no source code was copied.

## Docs

- [`docs/finalist-evaluation-handbook.md`](docs/finalist-evaluation-handbook.md)
- [`docs/deferred-ui.md`](docs/deferred-ui.md)
- [`docs/production-operations.md`](docs/production-operations.md)
- [`SECURITY.md`](SECURITY.md)

## License

[MIT](LICENSE).
