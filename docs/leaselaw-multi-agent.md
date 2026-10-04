# LeaseLaw — Cursor × OpenCode × ZCode

**Product:** LeaseLaw Navigator · Hack-Nation 7 Track 02 RealPage  
**Repo:** `/Users/efi/Hackathons/Hack-Nation-7`  
**App:** `apps/leaselaw/`

**Live coordination:** `docs/WIN_BOARD.md` + append-only `docs/AGENT_ADVICE_LOG.md`  
Agents advise each other every step. Goal = absolute Track 02 win.

## Roles

| Agent | Model / surface | Owns |
|-------|-----------------|------|
| **Cursor** | This session (orchestrator) | Extract/engine/eval, integrate, unblock, scoring hunt |
| **OpenCode** | `opencode/mimo-v2.6-flash-free` | Score panel UI, `/api/eval`, `src/extractors/**` |
| **ZCode** | ZCode.app (`docs/zcode-build-goal.md`) | Durable deploy + submission pack |

## Do not conflict

- Cursor owns `apps/leaselaw/src/extract_rules.py`, `engine.py`, `eval_harness.py`
- ZCode owns `apps/leaselaw/src/jurisdiction.py` and may extend `export_outputs.py`
- OpenCode may add rules under `apps/leaselaw/src/extractors/` and polish `main.py` HTML only after Cursor lands the baseline

## Acceptance (shared)

```bash
cd apps/leaselaw
python -m src.extract_rules
python -m src.export_outputs
python -m src.eval_harness
# T1–T5 pass; out/rules.json lookups.json changes.json exist
uvicorn src.main:app --port 8012
```

## Human-only

HackOS team/challenge select, dual submit, video upload, final send.
