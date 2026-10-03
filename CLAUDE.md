# CLAUDE.md

Start at **[AGENTS.md](AGENTS.md)**. That file is the source of truth for any AI (Claude, Cursor, Codex, OpenCode, ZCode).

## 30-second orientation

- **Active product:** LeaseLaw · `apps/leaselaw/` · Hack-Nation Track **02 RealPage**
- **Board:** `docs/WIN_BOARD.md` · advice log: `docs/AGENT_ADVICE_LOG.md`
- **Green check:** `cd apps/leaselaw && python -m src.eval_harness` → 5/5
- **Demo:** `uvicorn src.main:app --port 8012` → http://127.0.0.1:8012
- **Human-only:** HackOS submit, Google Form, email send, videos upload

## Do not confuse

| Thing | Path |
|-------|------|
| HackForge (idea engine) | `src/hackforge/` |
| LeaseLaw (competition entry) | `apps/leaselaw/` |
| Old empty workspace | `/Users/efi/Hackathons/Hack Nation` (ignore) |
