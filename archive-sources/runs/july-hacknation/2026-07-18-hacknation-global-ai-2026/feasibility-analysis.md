# Feasibility analysis

## concept-002
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: A working provenance-bound temporal evidence graph where removing or changing a real evidence node deterministically changes cited claims, counterfactual output, and the saved memo/audit trail.
- Min demo loop: Ingest one startup packet, extract timestamped evidence with citations, render the graph, run one node-removal counterfactual, regenerate the memo with unsupported claims removed, and persist a human override plus trace.
- Dependencies: Reliable access to pitch deck/public artifact inputs and a small fixed corpus with enough timestamped evidence to support meaningful trajectory changes., LLM/API access with stable structured-output behavior and trace logging during the demo., A credible evaluation rubric for unsupported investment claims versus sourced claims.
- Notes: Feasible if scoped to fixed fixtures and replayable demos. Risk rises sharply if live web ingestion, founder-history verification, patents, market context, or broad startup coverage are expected. The proposed 70% claim-reduction benchmark is easy to game unless the test set and baseline are frozen before judging.

## concept-003
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: A source-coordinate-to-field-to-rule-calculation verifier that blocks unsupported readiness statements, preserves user corrections/deletions, and never emits eligibility approval, denial, ranking, or scoring.
- Min demo loop: Upload two synthetic documents, extract fields with boxes, run one deterministic rule calculation, flag a stale or mismatched value, accept a user correction, remove unsupported packet text, and export the audit packet.
- Dependencies: Synthetic housing-document corpus with source-box ground truth, stale-date cases, OCR errors, and expected rule calculations., Clear RealDoor/program rules for one narrow program year, including effective dates and allowed non-decisioning boundaries., Document OCR/extraction stack that can return coordinates reliably enough for visible source-box review.
- Notes: This is one of the stronger concepts if aggressively narrowed. The biggest danger is overpromising policy coverage, OCR robustness, WCAG compliance, and legal-adjacent correctness. It should be killed only if no authoritative rule fixture or source-coordinate extraction is available quickly.

## concept-004
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: A Databricks-hosted triage workflow that computes evidence-status labels from real facility records, persists reviewer overrides across sessions, and changes shortlist ranking based on unresolved evidence gaps.
- Min demo loop: Load a small facility subset, classify two sparse records with cited evidence statuses, allow accept/override/no-call with reason, persist the review, reload the app, and show the follow-up queue changes.
- Dependencies: Actual Databricks Free Edition/App access with the needed dataset loaded and permissions for persistence, search, and MLflow tracing., Facility dataset fields rich enough to distinguish data gaps from access gaps without hallucinated capacity or doctor coverage., A defensible labeled or reviewed sample for measuring false access-gap reduction and no-call accuracy.
- Notes: Too many sponsor-tech and data-quality dependencies for a small team unless Databricks access and the facility dataset are already working. The core value depends on domain judgment and labels, not just app wiring. Without durable persistence and real sparse-record behavior, the demo collapses into a generic dashboard with scripted examples.

## mut-r4-02-negotiation-next-step-schedu
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: Given unseen or held-out transcript fixtures, extract itemized quotes, bind every recommendation to exact transcript evidence, reject unsupported leverage, and produce one bounded next action with an expiry-aware rationale.
- Min demo loop: Use 5-10 fixed transcript fixtures, normalize quotes, run honesty checks, choose one next action, and create a real or locally persisted scheduled callback with an audit trail.
- Dependencies: Reliable transcript fixtures with enough quote structure; cited GitHub source appears mismatched to the claimed consumer negotiation domain., Calendar/scheduler integration auth or a defensible local mock that judges accept as the last-mile action., LLM extraction/evidence-linking quality under messy transcripts, expiries, and honesty constraints.
- Notes: Useful demo shape, but the data story is weak: referenced sources do not obviously provide verified vendor-call transcripts. Risk is mostly evaluation credibility, not UI build.

## mut-r4-03-rental-packet-safety-interlo
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: The app must deterministically block decision-like transitions and generate evidence receipts tying extracted fields, rule version, and blocked language to source boxes.
- Min demo loop: Load one synthetic packet, extract boxed fields, run missing/expired checks, attempt an unsafe transition, block it, and export a neutral readiness receipt.
- Dependencies: Synthetic pay stub and benefit-letter fixtures with source boxes; real OCR is too risky unless tightly scoped., Clear versioned program-rule fixture and explicit prohibited eligibility language boundary., Reliable extraction provenance from document field to source box to receipt.
- Notes: Feasible if scoped to synthetic documents and deterministic rules. Do not attempt broad housing eligibility logic or production-grade OCR in a hackathon.

## mut-r4-04-facility-rule-regression-run
- Delivery risk: **high**
- Kill?: False
- Non-fakeable core: Executable regression tests must run against facility rows, detect a seeded sparse-field logic bug, and show evidence/no-call invariant failures with repeatable before/after results.
- Min demo loop: Cache a 50-row facility fixture, define 6-10 invariants, seed one classifier bug, run generated tests, display failing receipt and trace, then rerun after fix.
- Dependencies: Actual Databricks Free Edition/App access plus MLflow 3 tracing permissions; local-only fallback weakens track fit., Facility dataset availability and column semantics matching claims like numberDoctors, source URL, capacity, equipment., A credible classifier baseline and golden-label strategy; otherwise regression tests only test invented rules.
- Notes: Technically attractive but brittle because it stacks Databricks Apps, MLflow, fixture semantics, generated tests, and domain-specific labels. Keep the loop local-first, then add Databricks only if access is already working.

## mut-r4-05-checkroom-capital-allocator
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: The system must show that new contradictory evidence changes a constrained diligence allocation for defensible reasons, not just produce a memo or arbitrary ranking.
- Min demo loop: Use three startup packets, define a transparent scoring rubric, inject one contradiction, recompute hour/check allocation, and emit an evidence-linked audit of moved resources.
- Dependencies: Credible startup evidence packets with enough ground truth to evaluate value-of-information allocation., Access to any required ElevenLabs/GPT sponsor tech is unclear and not materially aligned with the claimed workflow., Subject-matter expertise in venture diligence to define scoring, uncertainty, contradictions, and check-review decisions.
- Notes: Kill or radically re-scope. It has poor track fit, mismatched required tech, weak data provenance, and high SME burden. The demo can be made, but judging credibility is fragile.

## mut-r4-06-quoteconflict-review-opener
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: Given transcript bundles, reduce them to the smallest evidence-linked conflict set that preserves price-changing disputes and opens a review task with callback questions.
- Min demo loop: Load three transcripts, extract quote assertions, identify 3-5 conflicts/refusals, create one review task with span links and callback wording, and compare against full-transcript baseline.
- Dependencies: Transcript fixtures with labeled conflicts; cited Devpost data source is not credible as negotiation transcript data., LLM or parser quality for quote assertion extraction and minimal conflict-set selection., Human-review workflow must be concrete enough to count as an action, not just another summary screen.
- Notes: More feasible than the scheduler because it avoids calendar auth. The central risk is that all meaningful evaluation depends on synthetic labels unless real call transcripts exist.

## mut-r4-07-facility-provenance-ledger
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: The app must persist reviewer accept/reject/revise decisions against claim-level evidence and prove unsupported facility claims cannot remain on the planning shortlist without an override record.
- Min demo loop: Use a 20-50 row fixture, create claim assertions, flag unsupported capacity/doctor claims, let a reviewer update ledger states, and show shortlist changes with timestamps and evidence links.
- Dependencies: Track and data alignment must be fixed; proposal says Databricks facility planning but declares RealPage and cites unrelated Devpost/source artifacts., Working Databricks App/Lakehouse persistence or a convincing local ledger fallback., Domain rules for distinguishing documentation gaps from plausible access gaps in sparse healthcare facility data.
- Notes: Kill in current form. It has severe internal inconsistency across track, user, data source, and sponsor tech. A salvageable Databricks-only version exists, but this candidate as written will look incoherent to judges.
