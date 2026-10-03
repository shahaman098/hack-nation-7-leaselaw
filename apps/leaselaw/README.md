# LeaseLaw Navigator — Hack-Nation 7 Track 02 (RealPage)

Address-level rental housing law answers with citations, as-of dates, and change tracking.

**Not legal advice.**

Agents/ops: repo [`AGENTS.md`](../../AGENTS.md) · [`docs/OPS_RUNBOOK.md`](../../docs/OPS_RUNBOOK.md) · scoped [`AGENTS.md`](AGENTS.md).

## Quick start

```bash
cd apps/leaselaw
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.extract_rules
python -m src.export_outputs
python -m src.eval_harness          # expect T1–T5 pass
uvicorn src.main:app --reload --port 8012
```

Open http://127.0.0.1:8012

## Pipeline

| Step | Command | Output |
|------|---------|--------|
| Extract | `python -m src.extract_rules` | `out/rules.json` |
| Export | `python -m src.export_outputs` | `out/lookups.json`, `out/changes.json` |
| Eval | `python -m src.eval_harness` | `out/eval-report.json` |

Starter pack (unpacked): `../../briefs/hack-nation-7-realpage-starter/participant-final-no-hour16 3/`  
Override with `LEASELAW_STARTER=/path/to/pack`.

## Change tests

Harness covers official T1–T5 (AB325 as-of, Hoboken/JC boundary, NJ FAIR Act, MA pending bills, MA rent-control negative).

If the scoring pack with `score.py` becomes available, run it on the **dev key** and paste the report into demo videos.

## Multi-agent

See `../../docs/leaselaw-multi-agent.md` (Cursor + OpenCode Mimo + ZCode).

## Submission

Prepare pack under `../../docs/hn7-submission-pack/`. **You** submit HackOS + Google Form + videos.
