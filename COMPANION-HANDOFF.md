# Companion handoff — Cursor ↔ ZCode

**Canonical repo (use this one):** `/Users/efi/Hackathons/Hack-Nation-7`

Do **not** continue editing `/Users/efi/Organized/05_Projects/Projects/Hackathon Engine` — that was a divergent Cursor copy. Winner-inspiration work has been ported here.

## Who did what

### ZCode (this tree, ahead on `main`)
- Leakage-controlled winner **backtest** harness (`evals/backtest/`)
- Feasibility-preserving **build-plan** stage after selection
- Codex reasoning-effort wiring (`HACKFORGE_CODEX_REASONING_EFFORT`)
- Real brief: `briefs/hacknation-global-ai-2026.md`
- Status notes: `evals/backtest/status.md`

### Cursor (ported into this tree)
- Verified-winner corpus: `corpora/verified-winners/seed.jsonl` (~27 rows)
- Pattern extraction: `src/hackforge/winners/`, `prompts/winner-patterns/v1.md`
- Inspiration scoring (30% + clone guard): `docs/inspiration-metric.md`
- Profile: `profiles/hack-nation.yaml` → `--profile hack-nation`
- Multi-track gate scoping (requirements apply only to declared track)
- Demo docs: `docs/hack-nation-submission.md`

## How to run (shared)

```bash
source .venv/bin/activate  # or the uv 3.12 env ZCode used
hackforge analyse \
  --profile hack-nation \
  --provider codex \
  --search-profile fast \
  --no-live-research \
  --no-visual-report
```

Optional dry-run:

```bash
hackforge analyse \
  --profile hack-nation \
  --dry-run --fixture-bundle fixtures/dry-run-bundle.json \
  --search-profile fast --no-visual-report --no-build-plan
```

Expect: `winner-patterns.json`, `inspiration-report.json`, inspiration section in `final-recommendation.md`, plus ZCode’s `build-plan.md` when not skipped.

## Split of work (suggested)

| Owner | Next |
|-------|------|
| **ZCode** | Finish/resume live analyse on `briefs/hacknation-global-ai-2026.md`; keep backtest protocol honest |
| **Cursor** | Wire/tests polish, dry-run E2E with profile, submission docs, avoid stomping backtest/build-plan |
| **Human** | Demo video + Devpost submit |

## Rules of engagement

1. One tree only (this path).
2. Don’t overwrite `evals/backtest/*` or `pipeline/build_plan.py` without reading `status.md`.
3. Don’t claim live backtest success without organizer-verified lists (see status.md).
4. Leave a short note in this file when you ship a meaningful chunk.

## Log

- **2026-10-03 Cursor:** Moved agent root here. Ported winner corpus/patterns/inspiration + `--profile hack-nation` into this tree without replacing build-plan/backtest. Multi-track gate scoping added on top of ZCode’s data-gate WAF fixes. `tests/test_inspiration.py` + multitrack gate test pass.
- **2026-10-03 Cursor (orchestrator):** Shipped **AppealPath Diff** MVP in `apps/api` + `apps/web` (GUI + deterministic `/api/analyze`). Dev: API `:8001`, UI `:5180`. ZCode handoff: `AGENTS.md`, `docs/zcode-build-goal.md`. API smoke: `tests/test_appeal_api.py`.
