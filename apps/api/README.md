# AppealPath Diff — API + CLI (no UI)

Deterministic rule-version diff and appeal evidence pack for the HackForge primary concept `idea-01-appeal-path-diff`.

## CLI demo (preferred)

```bash
cd apps/api/src
pip install -r ../requirements.txt

python cli.py --list-samples
python cli.py --sample case-03-deadline-miscalculation
python cli.py --sample case-03-deadline-miscalculation --json
```

## Optional HTTP API

```bash
cd apps/api/src
python -m uvicorn main:app --port 8012
curl -s http://localhost:8012/api/health
curl -s -X POST http://localhost:8012/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"notice_text":"..."}'
```

Default port **8012** avoids conflict with other local uvicorn apps on 8001.

## Tests

From repo root: `pytest tests/test_appeal_api.py -q`
