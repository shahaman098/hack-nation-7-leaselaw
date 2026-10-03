# STATUS — machine-readable snapshot for agents

Last updated: 2026-10-03 20:18 BST (Europe/London) · measured this turn

```yaml
competition: Hack-Nation 7
track: "02 RealPage"
product: LeaseLaw Navigator
product_path: apps/leaselaw
canonical_repo: /Users/efi/Hackathons/Hackathon-Idea-Search
disclaimer: Not legal advice
ops_runbook: docs/OPS_RUNBOOK.md

eval:
  harness: T1-T5
  last_measured: 5/5
  measured_at: "2026-10-03 20:18 BST"
  how: "python3 -m src.eval_harness · exit 0"
  report: apps/leaselaw/out/eval-report.json
  official_score_py: false   # pack is participant-no-scoring

artifacts:
  rules: apps/leaselaw/out/rules.json
  rules_count: 41
  lookups: apps/leaselaw/out/lookups.json
  changes: apps/leaselaw/out/changes.json

runtime:
  local: http://127.0.0.1:8012
  port: 8012
  health_this_turn: ok   # curl /health → ok:true, rules:41, addresses:500
  api_eval_this_turn: "passed:5 total:5"
  public_tunnel: ephemeral / often off
  live_url_file: docs/hn7-submission-pack/LIVE_URL.txt

open_work:
  - durable public deploy
  - official score.py if Drive pack appears
  - human HackOS + Form + videos

do_not:
  - submit forms
  - send email
  - use /Users/efi/Hackathons/Hack Nation as codebase
```

Human narrative board: [WIN_BOARD.md](WIN_BOARD.md). Ops: [OPS_RUNBOOK.md](OPS_RUNBOOK.md).
