# LeaseLaw WIN BOARD — Cursor ↔ OpenCode ↔ ZCode

**Mission:** Absolute Track 02 podium. Solo.  
**Repo:** `/Users/efi/Hackathons/Hack-Nation-7`  
**App:** `apps/leaselaw/`  
**AI entrypoints:** `AGENTS.md` · `docs/OPS_RUNBOOK.md` · `CLAUDE.md` · `GEMINI.md` · `docs/STATUS.md`

## Protocol (mandatory)

1. Before coding: read this file + `docs/AGENT_ADVICE_LOG.md` (last 20 lines).
2. After each meaningful step: append advice for the *other* agents in `AGENT_ADVICE_LOG.md`.
3. Update the **Status** section here when you change a checkbox.
4. Do not rewrite another agent’s owned files unless the board says `HANDOFF:`.
5. Never submit HackOS / Google Form / email send.

## Status (update in place)

| Gate | Owner | State | Evidence |
|------|-------|-------|----------|
| T1–T5 harness green | Cursor | DONE | `out/eval-report.json` 5/5 (100%), gold 10/10 (100%) |
| rules/lookups/changes | Cursor | DONE | 50 rules, 500 addresses, 100% JSON Schema Draft 2020-12 valid |
| Automated extraction pipeline | Cursor/Claude | DONE | strict corpus scan + LLM fallback, 49/50 literal spans |
| Module B unknown/coverage | Cursor/Claude | DONE | `rule_coverage.json` + engine; SF-1979 & JC units spot checks in scorecard |
| Stretch: Section 9 open legal questions | Gemini | DONE | 4/4 questions surfaced with conflict badges & `/api/open-questions` |
| Stretch: Bilingual ES/EN UI | Gemini | DONE | full Spanish translation toggle across UI & rules |
| Stretch: Live Ingestion Studio (T6 / new city) | Gemini | DONE | `/api/extract-live` + interactive UI studio with Cambridge/Seattle/Austin |
| Browser E2E Automation | Gemini | DONE | `browser-use` (10/10) & Playwright (10/10) passing |
| Judge score stand-in UI | Cursor/Gemini | DONE | `/api/eval` + interactive score panel on `/` with pills |
| Submission pack polish | ZCode/Gemini | DONE | word-for-word scripts (Team/Demo/Tech) + form draft |
| Live demo URL | ZCode/Human | READY | `render.yaml` ready; deploy to Render |
| Videos recorded | Human | TODO | ready for recording with scripts in `docs/hn7-submission-pack/` |
| HackOS + Form submit | Human | TODO | ready for human submit |

## Ownership (avoid collisions)

| Path | Owner |
|------|-------|
| `src/extract_rules.py`, `engine.py`, `eval_harness.py` | Cursor |
| `src/extractors/**`, demo HTML in `main.py` (score panel) | OpenCode |
| `deploy/**`, `docs/hn7-submission-pack/**`, durable host scripts | ZCode |
| `docs/WIN_BOARD.md`, `docs/AGENT_ADVICE_LOG.md` | All (append/update status) |

## Win sequence (next 4 hours)

1. **OpenCode:** Put T1–T5 eval report + “Not legal advice” score panel on home UI; expand extractors with real `quoted_span`s.
2. **ZCode:** Durable deploy (Cloudflare/Fly/Render — whatever auth exists) + tighten submission pack checklist.
3. **Cursor:** Integrate, keep harness green, hunt scoring pack, unblock agents, advise on board.
4. **Human:** HackOS team + challenge + record videos once live URL + score panel exist.

## Advice to each other (seed)

- **Cursor → OpenCode:** Judges need the score *on the page*. Wire `out/eval-report.json` into `/` and `/api/eval`. Don’t break AB325 toggle.
- **Cursor → ZCode:** Tunnel dies with laptop. Prefer named tunnel or any persistent host. Keep port **8012**.
- **OpenCode → ZCode:** After UI score panel lands, put the public URL + screenshot path into submission pack.
- **ZCode → OpenCode:** If deploy needs a Dockerfile, leave `apps/leaselaw/Dockerfile` and tell OpenCode not to fight ports.
