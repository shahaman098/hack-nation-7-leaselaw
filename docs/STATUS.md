# STATUS — machine-readable snapshot for agents

Last updated: 2026-10-03 (Europe/London)

```yaml
competition: Hack-Nation 7
track: "02 RealPage"
product: LeaseLaw Navigator
product_path: apps/leaselaw
canonical_repo: /Users/efi/Hackathons/Hackathon-Idea-Search
disclaimer: Not legal advice

eval:
  harness: T1-T5
  last_known: 5/5
  report: apps/leaselaw/out/eval-report.json
  official_score_py: false   # pack is participant-no-scoring

artifacts:
  rules: apps/leaselaw/out/rules.json
  lookups: apps/leaselaw/out/lookups.json
  changes: apps/leaselaw/out/changes.json

runtime:
  local: http://127.0.0.1:8012
  port: 8012
  public_tunnel: ephemeral / often off

open_work:
  - durable public deploy
  - official score.py if Drive pack appears
  - human HackOS + Form + videos

do_not:
  - submit forms
  - send email
  - use /Users/efi/Hackathons/Hack Nation as codebase
```

Human narrative board: [WIN_BOARD.md](WIN_BOARD.md).
