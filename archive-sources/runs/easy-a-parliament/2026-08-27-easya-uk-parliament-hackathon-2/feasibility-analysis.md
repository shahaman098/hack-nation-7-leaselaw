# Feasibility analysis

## concept-000
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: A live natural-language rule edit must compile into inspectable predicates, run against records, and change aggregate and row-level outcomes with traceable reasons.
- Minimum completion/proof loop: Prepare a small fictional grant or casework dataset, enter or edit one eligibility or priority rule live, show the parsed predicates, run current versus proposed outcomes, display affected records and segment deltas, then generate a one-page consequence brief with assumptions and uncertainty labels.
- Dependencies: Reliable LLM-to-structured-predicate parsing with guardrails so live edits do not produce invalid or misleading simulations., A synthetic civic dataset and policy-rule schema that are narrow enough to make before/after deltas defensible., Clear non-technical visualization of assumptions, affected groups, and uncertainty within a few minutes.
- Notes: Feasible for the build window if scoped tightly to one synthetic domain. Main risk is credibility: if the simulation looks like policy truth rather than bounded scenario analysis, MPs may distrust it. The AI is material, but only if parsing is visibly inspectable rather than hidden chatbot prose.

## mut-r1-01-casework-correction-receipt
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: A live correction request must be checked against evidence, converted into a structured patch, require reviewer confirmation, update the case record, and create a tamper-evident before/after receipt.
- Minimum completion/proof loop: Load a fictional case with evidence notes, submit one live correction, have the verifier classify support and cite evidence hashes, confirm the patch, update the case status, and open a receipt showing before value, after value, timestamp, reviewer, rationale, and immutable hash references.
- Dependencies: Fictional evidence bundles must be realistic enough for the AI verifier to make visibly grounded support decisions., Append-only signed event log or hash receipt must be implemented, not just described., Human confirmation and workflow-state update must be smooth enough for a live in-person demo.
- Notes: Stronger event fit than a generic assistant because the state change plus receipt is observable. Risk remains around overclaiming verification: the demo must say the AI supports review, not proves resident truth. No real casework data should be used.

## mut-r1-02-bounded-next-step-scheduler
- Delivery risk: **low**
- Kill?: False
- Non-fakeable core: The system must transform a live pitch note into structured unresolved claims, evaluate constraints, choose one bounded next action, and update the chosen action when inputs change.
- Minimum completion/proof loop: Paste a fictional pitch summary, extract unresolved claims and evidence needs, run against a synthetic calendar and dependency rules, display the selected 20-minute review action with owner, invitees, deadline, required input, stop condition, and reasons rejected alternatives were not chosen.
- Dependencies: A credible constraint fixture covering roles, availability, evidence gates, deadlines, and dependency rules., LLM extraction of claims and missing evidence from a short pitch note into structured scheduling inputs., A calendar-ready output that is understandable and visibly changes when the judge edits claim, deadline, or constraint.
- Notes: Most buildable concept, but also the easiest to dismiss as a smart to-do generator. To satisfy the AI-core requirement and demo bar, the constraint evaluation must be visible and the output must be more than a polished email or calendar invite.

## concept-004
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: The demo must ingest event records, score and cluster anomalies, link each alert to exact hashed raw records, and demonstrate that later feedback changes labels without changing prior evidence hashes.
- Minimum completion/proof loop: Load a synthetic procurement CSV, hash raw records into a local ledger, run anomaly scoring, open the top alert for split invoices or threshold avoidance, show implicated records and feature rationale, mark feedback, then show the original evidence hashes remain unchanged.
- Dependencies: Synthetic procurement or grant-event data with seeded anomalies that are realistic but simple enough to explain quickly., Interpretable anomaly scoring that can expose feature-level rationale without requiring ML expertise from the audience., Reliable evidence hashing and append-only alert references that remain stable after feedback changes.
- Notes: Feasible if the team avoids building a broad fraud platform. The hard part is making anomaly detection and cryptographic anchoring legible to non-technical parliamentarians in minutes. It should be framed as audit triage, not corruption detection.
