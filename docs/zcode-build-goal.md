# ZCode Goal — LeaseLaw ABSOLUTE WIN (Track 02)

**Approve plan → Start building. Read `docs/WIN_BOARD.md` + append to `docs/AGENT_ADVICE_LOG.md` after each step.**

## Outcome

Make LeaseLaw submission-proof for Hack-Nation 7 Track 02 RealPage.

## You own

1. **Durable public deploy** of `apps/leaselaw` (not only laptop tunnel). Prefer whatever is already authed (`wrangler` is on PATH). Keep API on a public HTTPS URL.
2. **Submission pack** under `docs/hn7-submission-pack/` — LIVE_URL, checklist, exact demo clicks.
3. Advise OpenCode/Cursor on the board if deploy needs Dockerfile / env changes.

## Do not own / do not break

- Do not rewrite `extract_rules.py` / `engine.py` / `eval_harness.py` unless Cursor marks `HANDOFF:`.
- Do not submit HackOS or Google Form.
- Do not kill Cursor’s local `:8012` without replacing it.

## Acceptance

```bash
cd /Users/efi/Hackathons/Hackathon-Idea-Search/apps/leaselaw
python -m src.eval_harness   # must stay 5/5
# Public URL returns /health ok:true
# docs/hn7-submission-pack/LIVE_URL.txt updated
# Append advice to docs/AGENT_ADVICE_LOG.md
```

## Context for teammates

- OpenCode (Mimo free): score panel UI + more corpus rules.
- Cursor: orchestrator, harness, scoring-pack hunt, integration.
- Product: address → cited rules → as-of toggle → T1–T5.
