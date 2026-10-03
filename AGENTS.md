# AGENTS.md — read this first (any AI)

**Repo root:** `/Users/efi/Hackathons/Hackathon-Idea-Search`  
**Human:** solo · Hack-Nation 7 · podium-first  
**User submits only** — never HackOS / Google Form / email final send / `git push` unless explicitly asked.

---

## What this repo is

Two layers in one tree:

| Layer | What | Where |
|-------|------|--------|
| **HackForge** | Idea search / ranking engine for competitions | `src/hackforge/`, `briefs/`, `runs/`, `prompts/` |
| **LeaseLaw (ACTIVE BUILD)** | Hack-Nation 7 **Track 02 RealPage** product | `apps/leaselaw/` |

If the user is talking about “the product”, “winning”, “Track 02”, or “LeaseLaw”, work in **`apps/leaselaw/`**.

Legacy pointer folder `/Users/efi/Hackathons/Hack Nation` is empty except a README — ignore it. Playbook/CV live in `hack-nation/`.

---

## Current mission (update when it changes)

**Ship LeaseLaw Navigator for Track 02 RealPage** so judges see: address → cited rules → as-of toggle → T1–T5 green → score panel on `/`.

Live coordination board: [`docs/WIN_BOARD.md`](docs/WIN_BOARD.md)  
Advice between agents: [`docs/AGENT_ADVICE_LOG.md`](docs/AGENT_ADVICE_LOG.md) (append-only)

### Done (do not redo blindly)

- Corpus extract → `apps/leaselaw/out/rules.json`
- Lookups for 500 addresses → `out/lookups.json`
- Changes T1–T5 → `out/changes.json`
- Harness T1–T5 pass → `out/eval-report.json`
- UI + `/api/eval` judge score panel on `/`
- Jurisdiction mapping (`src/jurisdiction.py`)

### Still open

- Official `score.py` (starter pack is **no-scoring**)
- Durable public deploy (not only laptop + quick tunnel)
- Human: HackOS team, dual submit, videos

---

## Map (where to look)

```
apps/leaselaw/           ← PRODUCT
  src/main.py            FastAPI + demo HTML
  src/extract_rules.py   corpus → rules.json
  src/engine.py          coverage / as-of / supersession
  src/eval_harness.py    T1–T5
  src/export_outputs.py  rules + lookups + changes
  src/jurisdiction.py    legal_city (Boston neighborhoods)
  src/extractors/        optional extra rules (OpenCode)
  out/                   generated artifacts
  deploy/                deploy notes for ZCode
briefs/hack-nation-7-realpage-starter/participant-final-no-hour16 3/
                         official starter (500 addrs, 54 texts, T1–T5)
docs/hn7-go-brief.md     demo script + must-ship
docs/hn7-decision-matrix.md
hack-nation/             playbook + CV
```

---

## Multi-agent ownership (avoid collisions)

| Agent | Owns |
|-------|------|
| **Cursor** | `extract_rules.py`, `engine.py`, `eval_harness.py`, integrate, unblock |
| **OpenCode** (`opencode/mimo-v2.6-flash-free`) | `src/extractors/**`, UI polish if board says so |
| **ZCode** | Durable deploy + `docs/hn7-submission-pack/` per `docs/zcode-build-goal.md` |

Before coding: read `docs/WIN_BOARD.md` + last entries of `docs/AGENT_ADVICE_LOG.md`.  
After a meaningful step: append advice for the other agents.

---

## Commands that must stay green

```bash
cd apps/leaselaw
python -m src.extract_rules
python -m src.export_outputs
python -m src.eval_harness          # expect passed 5/5
uvicorn src.main:app --host 127.0.0.1 --port 8012
# open http://127.0.0.1:8012  — Not legal advice + score panel
```

Claims discipline: do not say “done / working / deployed” without measuring this turn.

---

## Hard rules

1. **Not legal advice** — keep disclaimer on UI and API responses.
2. Rules need real `quoted_span` substrings from corpus when possible.
3. Failed/struck laws (e.g. MA rent ballot) must **not** appear as rent caps that `applies`.
4. No secrets in commits. No `--no-verify`. No force-push.
5. Prefer small diffs. Do not rewrite HackForge engine unless the task is about HackForge.

---

## Claude / Codex / OpenCode / ZCode

- **Claude Code:** also see [`CLAUDE.md`](CLAUDE.md) (points here).
- **Cursor:** `.cursor/rules/` always-apply project rule.
- **OpenCode prompt:** `docs/opencode-win-prompt.txt`
- **ZCode goal:** `docs/zcode-build-goal.md`

When unsure what “done” means → `docs/WIN_BOARD.md` Status table.
