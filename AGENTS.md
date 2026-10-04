# AGENTS.md — read this first (any AI)

**Public submission repo:** LeaseLaw only (`apps/leaselaw/`). HackForge is **not** published here (local-only on your machine if present).

**Repo root:** `/Users/efi/Hackathons/Hack-Nation-7`  
**Product:** Hack-Nation 7 **Track 02 RealPage** — LeaseLaw Navigator  
**User submits only** — never HackOS / Google Form / email final send / `git push` unless explicitly asked.

---

## Where to work

| Path | Role |
|------|------|
| `apps/leaselaw/` | FastAPI app, engine, extraction, `out/`, tests |
| `docs/OPS_RUNBOOK.md` | Ports, artifacts, deploy |
| `docs/WIN_BOARD.md` | Status + agent coordination |
| `docs/hn7-submission-pack/` | LIVE_URL, form drafts, video scripts |

**Live URL:** https://leaselaw-navigator.onrender.com  
**Demo port:** **8012** · **Not legal advice** on UI/API

---

## Green check

```bash
cd apps/leaselaw
python3 -m src.eval_harness   # 5/5
python3 -m pytest -q tests
uvicorn src.main:app --host 127.0.0.1 --port 8012
```

---

## Hard rules

1. **Not legal advice** — disclaimer on UI and API.
2. Rules need real `quoted_span` substrings from corpus when possible.
3. Failed/struck laws must **not** appear as rent caps that `applies`.
4. No secrets in commits.

See [`apps/leaselaw/AGENTS.md`](apps/leaselaw/AGENTS.md) for module map.
