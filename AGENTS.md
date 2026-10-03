# HackForge + AppealPath Diff — agent orchestration

## Canonical repo

`/Users/efi/Hackathons/Hackathon-Idea-Search`

## Roles

| Agent | Responsibility |
|-------|----------------|
| **HackForge (CLI)** | Competition intel, idea selection, `runs/*/build-plan.md` |
| **ZCode** | Long-horizon implementation in `apps/api` after plan approval |
| **Cursor** | Orchestrator: unblocks ZCode, fills gaps, verifies demo loop |

## Selected product (Hack-Nation dry run)

- **Concept:** Appeal Path Diff (`idea-01-appeal-path-diff`)
- **Run artifacts:** `runs/2026-10-03-hack-nation-tracks/`
- **Build plan:** `runs/2026-10-03-hack-nation-tracks/build-plan.md`
- **Deliverable shape:** **CLI + optional API only — no web UI** (operator preference)

## ZCode handoff

When planning is approved in ZCode, start building against `apps/api` only.

### Goal prompt (paste into ZCode)

```
Build AppealPath Diff per runs/2026-10-03-hack-nation-tracks/build-plan.md.

Stack: apps/api/src/main.py + apps/api/src/cli.py (terminal demo).
Demo: python cli.py --sample case-03-deadline-miscalculation → wrongful-rule flag, clause diff, checklist, audit JSON with --json.
Optional: uvicorn on port 8012 for /api/analyze. Do not build or polish a web UI.
No demo video unless the human asks.
```

## Verify before claiming done

```bash
cd apps/api/src
python cli.py --sample case-03-deadline-miscalculation
# from repo root:
pytest tests/test_appeal_api.py -q
```

## Out of scope unless asked

- Web UI (`apps/web` is legacy / unused)
- Devpost / HackOS submission clicks
- Demo video render
