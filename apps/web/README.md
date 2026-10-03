# AppealPath Diff — web UI (not used)

Operator does **not** want a UI. Use `apps/api/src/cli.py` instead. This folder is kept only as an optional sketch.

## Run (with API)

```bash
# Terminal 1 — API
cd apps/api
pip install -r requirements.txt
cd src
python -m uvicorn main:app --reload --port 8001

# Terminal 2 — UI (port 5180; proxies /api → 8001)
cd apps/web
npm install
npm run dev
```

Open http://localhost:5180 — load **case-03-deadline-miscalculation** and run analysis.
