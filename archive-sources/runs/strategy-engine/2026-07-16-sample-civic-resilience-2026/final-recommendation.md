# Final recommendation: Sample Civic Resilience Hackathon 2026

## Primary concept
**Working title:** FOI Failure Chain Tracer
**Internal id:** `institutional-foi-failure-chain-tracer-2`
**Primary user:** Council FOI officers before statutory breach
**Painful workflow:** Hunting which handoff stalled a request across teams
**Imported mechanism:** Failure-chain / fault-tree reconstruction _(from Reliability engineering)_
**Data sources:** Anonymized FOI case log CSV, Team ownership map
**Core computation:** Infer most likely stalled edge in the process graph from timestamps
**Last-mile action:** Create escalation ticket with evidence timeline
**Visible transformation:** Blind inbox → pinpointed bottleneck + escalation draft
**Killer demo:** Show live clock near breach → highlight failing handoff → draft escalation
**Hard-to-fake advantage:** Stateful case timeline with computed bottleneck
**Sponsor dependency:** Managed Postgres for case state

## Why this concept was selected
Votes={'A': 4, 'B': 1, 'C': 1}; disagreements=2

## Judge disagreement (do not average away)
- Judge disagreement — A: technical, product, domain, demo-risk | B: sponsor | C: contrarian
- Do not average automatically; inspect tradeoffs (novelty vs demo reliability vs sponsor fit).
- None (inspect vote table anyway)

### Judge votes
- **technical** → A: Clearest hard-to-fake computation with auditable trail
- **product** → A: Immediate workflow collapse for a constrained user
- **sponsor** → B: Stronger optional use of managed data store for state
- **domain** → A: Addresses a real administrative failure mode
- **demo-risk** → A: Offline fixture-friendly demo loop
- **contrarian** → C: Preserves an outlier optimization story

## Closest competing projects
- institutional-foi-failure-chain-tracer-2 (prior-run:2026-07-16-sample-civic-resilience-2026)
- Collision risk: medium
- Observable differentiator: Stateful case timeline with computed bottleneck
- Differentiator substantive?: True

## Critical assumptions
- Data exists and is accessible: Anonymized FOI case log CSV, Team ownership map
- Delivery risk: medium
- Technical risk note: Synthetic data believability

## Technical proof sketch (not an architecture)
- Critical computation: Infer most likely stalled edge in the process graph from timestamps
- Required data: Anonymized FOI case log CSV, Team ownership map
- Most dangerous dependency: Managed Postgres for case state
- Minimum demonstrable loop: Show live clock near breach → highlight failing handoff → draft escalation

## Forty-eight-hour scope
- One user: Council FOI officers before statutory breach
- One workflow: Hunting which handoff stalled a request across teams
- One demo moment: Show live clock near breach → highlight failing handoff → draft escalation
- Cut anything that does not improve the killer demo.

## Primary failure risk
fallback feasibility stub | HackRep common stacks: javascript, python, react, node, firebase, flask

## Red team
- Conditional acceptance: True
- Prefer backup instead: False
- Fatal flaws: []
- Survive if: ['Guidance snapshot fixtures remain convincing']

## Backup concept
**Appeal Path Diff** (`institutional-appeal-path-diff-0`)
- User: Social-care caseworkers filing benefit appeal packs
- Mechanism: Configuration drift detection + temporal fault trees
- Demo: Paste decision date + letter → show guidance diff → emit required evidence list with timestamps

## Rejected / not advanced
- `institutional-permit-queue-fairness-simulator-1` — Permit Queue Fairness Simulator: Solver demo may feel abstract without UX polish | hard-ban topology
- `institutional-grant-match-abuse-detector-3` — Grant Match Abuse Detector: Document parsing quality risk
- `institutional-clinic-no-show-pool-4` — Clinic No-Show Pool: Health data sensitivity in live settings
- `systems_or-appeal-path-diff-0` — Appeal Path Diff: May require careful sourcing of archived guidance pages
- `systems_or-permit-queue-fairness-simulator-1` — Permit Queue Fairness Simulator: Solver demo may feel abstract without UX polish | hard-ban topology
- `systems_or-foi-failure-chain-tracer-2` — FOI Failure Chain Tracer: Needs a plausible synthetic log for demo
- `systems_or-grant-match-abuse-detector-3` — Grant Match Abuse Detector: Document parsing quality risk
- `systems_or-clinic-no-show-pool-4` — Clinic No-Show Pool: Health data sensitivity in live settings
- `edge_users-appeal-path-diff-0` — Appeal Path Diff: May require careful sourcing of archived guidance pages
- `edge_users-permit-queue-fairness-simulator-1` — Permit Queue Fairness Simulator: Solver demo may feel abstract without UX polish | hard-ban topology
- `edge_users-foi-failure-chain-tracer-2` — FOI Failure Chain Tracer: Needs a plausible synthetic log for demo
- `edge_users-grant-match-abuse-detector-3` — Grant Match Abuse Detector: Document parsing quality risk
- `edge_users-clinic-no-show-pool-4` — Clinic No-Show Pool: Health data sensitivity in live settings
- `incentives-appeal-path-diff-0` — Appeal Path Diff: May require careful sourcing of archived guidance pages
- `incentives-permit-queue-fairness-simulator-1` — Permit Queue Fairness Simulator: Solver demo may feel abstract without UX polish | hard-ban topology
- `incentives-foi-failure-chain-tracer-2` — FOI Failure Chain Tracer: Needs a plausible synthetic log for demo
- `incentives-grant-match-abuse-detector-3` — Grant Match Abuse Detector: Document parsing quality risk
- `incentives-clinic-no-show-pool-4` — Clinic No-Show Pool: Health data sensitivity in live settings
