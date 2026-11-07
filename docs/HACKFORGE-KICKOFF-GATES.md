# HackForge “10/10” kickoff gates (Hack-Nation 7)

**Option B:** trust HackForge’s **live** run on real HackOS tracks, then **build the primary** recommendation (manual or `hackforge develop`).

HackForge is **not** a proven winner oracle — backtests are **inconclusive** (`evals/backtest/status.md`). These gates mean: **the pipeline is trustworthy for tonight**, not that placement is guaranteed.

## Scorecard (must be green before live analyse)

| # | Gate | Command / check | Pass criteria |
|---|------|-----------------|---------------|
| 1 | Runtime | `hackforge doctor --provider codex --strict --live` | Codex authenticated; no FAIL lines |
| 2 | Tests | `make test-fast` | All tests pass |
| 3 | Dry pipeline | `./scripts/run-hack-nation-idea-search.sh dry` | `run-status.json` → `"status": "complete"` |
| 4 | Real brief | `briefs/hack-nation-7-kickoff.md` | No `PLACEHOLDER`; paste **all** official tracks from HackOS |
| 5 | Live analyse | `./scripts/run-hack-nation-idea-search.sh live` | New `runs/<slug>/final-recommendation.md` + `build-plan.md` |
| 6 | Human read | Open `final-recommendation.md` | Primary + backups make sense; note judge disagreements |
| 7 | Build | Your choice | Implement `build-plan.md` **or** `hackforge develop runs/<slug> --provider codex --execute` |

Optional (quality, not blocking): `pip install -e ".[collision]"` + `hackforge corpus build-index` for stronger collision evidence.

## At kickoff (17:00 UK) — operator + agent

| Who | Action |
|-----|--------|
| **You** | Kickoff stream; copy HackOS **Challenges** → `briefs/hack-nation-7-kickoff.md`; create HackOS **team** |
| **You** | Say **“go live idea search”** (explicit approval for Codex run) |
| **Agent** | Run gates 1–3 if not already green; run gate 5; summarize primary + backups + risks |
| **You** | Confirm **one** concept (or override with `hackforge override`) |
| **Agent** | Scaffold/build per `build-plan.md` until deploy URL + repo ready |
| **You** | Videos + HackOS submit (agent prepares scripts/checklists only) |

## Autonomy (default for Option B)

**Autonomous after your “go”:** code, tests, deploy candidates, README, video scripts, HackForge `develop` file writes under `runs/*/product/`.

**Not autonomous:** live analyse without go; HackOS/Luma submit; OAuth; choosing track if you disagree with the recommendation.

## Skills hint (for analyse)

Pass your stack so feasibility scoring fits you:

```bash
export HACKFORGE_SKILLS="Python, FastAPI, LangGraph, RAG, React, TypeScript, AWS, hackathon winner (NVIDIA London, Gemini UI Navigator)"
./scripts/run-hack-nation-idea-search.sh live
```

(Or add `--skills` to the script if wired.)
