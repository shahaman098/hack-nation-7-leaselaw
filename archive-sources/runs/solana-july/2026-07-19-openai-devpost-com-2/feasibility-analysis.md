# Feasibility analysis

## concept-004
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: Given a real or realistic trace, the system must extract evidence-linked process events, perturb specific trace elements, rerun scoring, and show a reproducible assessment delta tied to trace IDs.
- Min demo loop: Use one fixed learner repository fixture, parse commits/prompts/test logs into trace events, call GPT-5.6 once for structured event labels, run two deterministic counterfactual removals, and update an assessment status with cited event IDs.
- Dependencies: Actual GPT-5.6 API access, model name, auth, quota, and predictable structured-output behavior before the deadline., A credible learner-process dataset with prompts, commits, tests, notes, and artifact snapshots; the cited data source does not obviously match the education workflow., Deterministic trace schema and counterfactual evaluator whose outputs are stable enough to demo without looking like arbitrary LLM relabeling.
- Notes: Too much depends on inventing high-quality process-history data and defensible education assessment logic in two days. The hard part is not the UI; it is making counterfactual rubric sensitivity credible instead of a scripted LLM judgment. Kill unless the team already has a clean flight-recorder-style trace dataset and GPT-5.6 access working today.

## concept-005
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: The app must actually evaluate allocation constraints, detect a seeded contradiction, identify affected applicants, block an invalid commit, then allow a corrected ruleset to commit changed statuses.
- Min demo loop: Load 30 fixture applicants and 12 slots, run a baseline allocator, apply explicit constraints, show one eligibility violation and one tie case, block commit, fix constraint/settings, then export committed statuses and an audit ledger.
- Dependencies: A small, explicit policy language or constraint representation; natural-language policy parsing cannot be trusted as the source of truth in the demo., A deterministic solver/checker that can produce minimal counterexamples and block commits reliably., GPT-5.6 access for policy explanation and rationale generation, with fallback cached outputs for demo reliability.
- Notes: This is the strongest candidate if the team keeps GPT out of the enforcement path. Use GPT-5.6 only to translate/explain, and make the constraint engine deterministic. Risk rises sharply if they attempt open-ended policy parsing or real integrations.

## concept-003
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: The system must extract dated events with source spans, build a dependency graph, identify a missing or contradictory prerequisite, accept new evidence, and update node state and deadline risk reproducibly.
- Min demo loop: Use three seeded text documents, extract events and citations through GPT-5.6, build a simple prerequisite graph, flag one missing service-date proof, ingest one receipt, recalculate the graph state, and export an appointment brief.
- Dependencies: Legally safe scope and copy; the product must avoid jurisdiction-specific legal advice while handling high-stakes appeal materials., High-quality synthetic or licensed case documents with dates, notices, receipts, contradictions, and source spans., Reliable document extraction with citations across messy uploads; OCR/PDF parsing can consume the entire remaining schedule.
- Notes: The social-impact angle is strong, but the delivery surface is large: document ingestion, citation fidelity, legal-scope risk, redaction, deadline logic, and user trust. In 48 hours it should only survive as a narrow fixture demo with text inputs, not as a general appeal reconstructor.

## mut-r4-01-tracepatch-verifier
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: A verifier that runs real setup/test commands, links rule requirements to concrete repo evidence, and applies a diff that survives rerun verification.
- Min demo loop: One seeded repo, cached rules, failing setup/readme mismatch detection, generated README patch, accepted writeback, rerun showing requirement status changed to verified.
- Dependencies: Actual access to GPT-5.6 API/model name and stable auth before recording, Reliable local repo scanning across README, scripts, logs, demo transcript, and Codex session notes, Official rules fixture must be current and accurately encoded
- Notes: Good hackathon scope if it is narrowed to one repo type and a fixed rule set. Biggest risk is overclaiming generalized attestation; keep it as submission-readiness verification with deterministic checks.

## mut-r4-02-nextstep-queue-scheduler
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: A scheduler that takes decision records plus capacity constraints and writes a next-action queue where every actionable case has an owner and time or an explicit blocker.
- Min demo loop: Import 30-case fixture, detect unscheduled actionable cases, generate owner/time assignments, flag blocked prerequisites, export CSV, and show zero unowned actionable cases.
- Dependencies: Usable CanopyOps-derived fixture or replacement synthetic operations dataset with clear licensing, Constraint schema for owner, due time, prerequisite, service window, and capacity, Calendar/CSV export must work offline without third-party permission delays
- Notes: Feasible if no real calendar integration is attempted. Risk is domain ambiguity: volunteer clinic, clinic admin, and operations scheduling each imply different constraints; choose one.

## mut-r4-03-unsafe-filing-interlock-rece
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: A pre-submit state machine that blocks release based on source-grounded prerequisite checks, preserves negative evidence, and updates only after new evidence satisfies the missing dependency.
- Min demo loop: One filing type, three seeded packets, parser extracts dates/attachments, missing service proof blocks submit, receipt is generated, adding proof changes state to released.
- Dependencies: Procedurally valid appeal-packet fixtures and prerequisite rules for one narrow filing domain, Careful legal/administrative disclaimers and no unauthorized legal advice positioning, Robust document parsing/redaction for uploaded sensitive files
- Notes: Too much subject-matter and liability risk for the deadline unless drastically narrowed to a fictional or hackathon submission packet. Current concept invokes benefits, housing, school, immigration, and healthcare, which is not credible in 48 hours.

## mut-r4-04-rubric-regression-lab
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: An executable regression runner that compares old versus new rubric behavior across fixed traces and blocks release when policy thresholds are exceeded.
- Min demo loop: Two rubric versions, 30 fixed learner traces, old/new scoring comparison, seven seeded outcome deltas detected, release gate blocks, restoring clause passes.
- Dependencies: Historical learner-trace fixtures with expected outcomes and licensing, Deterministic rubric evaluator or constrained scoring harness, Clear invariant definitions that humans can understand and audit
- Notes: Strongest education candidate if the team avoids real LMS integration and keeps the rubric evaluator deterministic. Main risk is that GPT-5.6 is peripheral unless it actually generates useful test cases or explanations.

## mut-r4-05-shiftsplice-live-constraint-
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: A reallocation engine that removes a resource, computes a replacement schedule satisfying hard constraints, and emits traceable before/after diffs plus held cases.
- Min demo loop: Load 24 appointments, remove one room, detect violations, compute five moves and two holds, verify zero hard violations, export dispatch CSV.
- Dependencies: A small constraint solver or well-scoped search algorithm that reliably finds minimal valid reallocations, Clean schedule fixture with rooms, staff roles, priorities, access needs, and hard constraints, CSV import/export and dispatch packet generation must be reliable during demo
- Notes: Feasible only with a tiny deterministic solver and fixed constraints. Track fit is mislabeled as Developer Tools despite the user/workflow being work productivity; this can weaken submission framing.

## mut-r4-07-appeal-ledger-procedural-evi
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: A provenance ledger that links each appeal claim to document evidence, quarantines assumptions, tracks contradictions, and updates claim status after new evidence is added.
- Min demo loop: Import one synthetic appeal folder, extract dated events, mark unsupported claims, add one missing notice, update ledger statuses, export evidence checklist.
- Dependencies: Narrow appeal domain with realistic fixture documents and prerequisite taxonomy, Privacy-safe local handling and redaction of sensitive personal documents, Reliable deadline extraction and contradiction detection from messy inputs
- Notes: This is safer than the filing interlock but still too broad and expertise-heavy across benefits, housing, school, insurance, and healthcare. Kill unless narrowed to fictional documents or one benign administrative workflow.

## mut-r4-08-labmethod-mirror-counterfact
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: A counterfactual experiment runner that changes one design assumption at a time, recomputes analysis on fixed data, and explains conclusion drift against rubric-linked assumptions.
- Min demo loop: One protocol, one dataset, three perturbations, recomputed effect estimates, one conclusion flip, and a revise-design state with assumption IDs.
- Dependencies: Research-methods expertise to define valid perturbations and avoid nonsense causal claims, Synthetic datasets that produce credible numeric conclusion drift, Deterministic analysis runner for baseline and counterfactual protocols
- Notes: Interesting but fragile. Without a real statistical engine and methods expertise, it risks becoming an LLM critique UI with staged numbers. Too ambitious for the deadline unless reduced to one canned experimental design pattern.
