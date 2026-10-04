# STATUS — machine-readable snapshot for agents

Last updated: 2026-10-04 · measured this turn

```yaml
competition: Hack-Nation 7
track: "02 RealPage"
product: LeaseLaw Navigator
product_path: apps/leaselaw
canonical_repo: /Users/efi/Hackathons/Hack-Nation-7
disclaimer: Not legal advice
ops_runbook: docs/OPS_RUNBOOK.md

eval:
  harness: T1-T5
  last_measured: 5/5
  gold: 10/10
  how: "python3 -m src.eval_harness · exit 0"
  report: apps/leaselaw/out/eval-report.json
  quality_scorecard: true
  official_score_py: false

artifacts:
  rules: apps/leaselaw/out/rules.json
  rules_count: 174
  lookups: apps/leaselaw/out/lookups.json
  lookups_format: "{as_of, lookups: {address_id: [...]}}"
  changes: apps/leaselaw/out/changes.json
  changes_format: "T1-T5 affected_address_ids"
  debug: apps/leaselaw/out/debug/

runtime:
  local: http://127.0.0.1:8012
  port: 8012
  deploy: render.yaml (repo root, docker context .)
  live_url_file: docs/hn7-submission-pack/LIVE_URL.txt

open_work:
  - human Render deploy + LIVE_URL.txt
  - optional live LLM re-extract with ANTHROPIC_API_KEY
  - human HackOS + Form + videos

do_not:
  - submit forms
  - send email
```

Human narrative board: [WIN_BOARD.md](WIN_BOARD.md). Ops: [OPS_RUNBOOK.md](OPS_RUNBOOK.md).
