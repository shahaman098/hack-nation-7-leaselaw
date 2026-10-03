# ZCode Goal — AppealPath Diff (start building)

**When planning is approved in ZCode, click Start building / approve the plan, then execute this goal.**

## Outcome

Ship a judge-demo-ready **Appeal Path Diff** product aligned with `runs/2026-10-03-hack-nation-tracks/final-recommendation.md` (primary concept `idea-01-appeal-path-diff`).

## Acceptance

1. `apps/api/src/main.py` serves `/api/analyze` with deterministic rule-version diff + evidence checklist.
2. **No web UI** — terminal demo via `python cli.py --sample case-03-deadline-miscalculation`.
3. Optional API on port **8012** for `/api/analyze`.
4. `pytest tests/test_appeal_api.py` passes.
5. No demo video unless the human asks.

## Commands

```bash
cd apps/api/src && python -m uvicorn main:app --reload --port 8001
cd apps/api/src && python cli.py --sample case-03-deadline-miscalculation
pytest tests/test_appeal_api.py -q
```

## Cursor orchestrator status

Cursor completed the minimum loop (API + GUI + tests + `AGENTS.md`). ZCode should harden styling, add calendar export, and wire Hack-Nation track copy if time remains.
