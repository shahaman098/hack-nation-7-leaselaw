# LeaseLaw Navigator

**Hack-Nation 7 · Track 02 RealPage** — address + as-of date → cited rental housing rules with quotes.

**Not legal advice.** Prototype for the MIT Rental Housing Law Navigator challenge.

| | |
|--|--|
| **Live demo** | https://leaselaw-navigator.onrender.com |
| **Ops** | [`docs/OPS_RUNBOOK.md`](docs/OPS_RUNBOOK.md) |
| **Submission pack** | [`docs/hn7-submission-pack/`](docs/hn7-submission-pack/) |

## Quick start

```bash
cd apps/leaselaw
pip install -r requirements.txt
python3 -m src.export_outputs
python3 -m src.eval_harness    # expect T1–T5 5/5
uvicorn src.main:app --host 127.0.0.1 --port 8012
```

Open http://127.0.0.1:8012 — score panel loads from `/api/eval`.

## Docker / Render

Repo-root `Dockerfile` + `render.yaml` deploy the bundled starter under `apps/leaselaw/deploy/starter-pack/`. See [`apps/leaselaw/deploy/RENDER-STEPS.md`](apps/leaselaw/deploy/RENDER-STEPS.md).

## Verify

```bash
curl -sS https://leaselaw-navigator.onrender.com/health
curl -sS https://leaselaw-navigator.onrender.com/api/eval
```
