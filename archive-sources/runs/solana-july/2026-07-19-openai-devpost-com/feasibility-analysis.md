# Feasibility analysis

## concept-002-3
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: The system must actually apply or reject a repo checkpoint based on real command execution and produce a lesson artifact grounded in the resulting diff and logs.
- Min demo loop: Use one small public repo, one lesson objective, three checkpoints, and one intentional failing checkpoint. Run verifier, show failure, have Codex/GPT-5.6 repair or revise it, rerun tests, and export a verified lesson bundle with transcripts.
- Dependencies: Reliable GPT-5.6 API access with enough quota for repeated repo-analysis, repair, and explanation loops, A tightly scoped fixture repo with deterministic install/test commands and permissive license, Sandboxed patch runner that can safely clone, edit, run tests, capture logs, and recover from failures during demo
- Notes: Feasible only if the team stops trying to support arbitrary repositories. General repo ingestion, screenshots, branch management, and explanation grounding are a large integration surface. The winning proof is not the UI; it is deterministic verification from a fresh clone. Model cost is moderate but repeated repair loops can spike. Main risk is brittle environment setup and flaky generated constraints, not data access.

## concept-003
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: The project must run identical checks across baseline, assisted, and ablated variants and produce a credible receipt tying requirements, code changes, approvals, tests, and metric deltas together.
- Min demo loop: Build one tiny CRUD/internal workflow app with one requested change. Capture a baseline plan, apply a Codex-assisted branch, remove or replace the labeled model-dependent patch for ablation, run the same test suite across all three, and emit a receipt showing pass/fail and metric deltas.
- Dependencies: A synthetic internal-tool repo with known baseline, assisted, and ablated branches plus deterministic metrics, Clear definition of what counts as a model-dependent change and how ablation is computed, Git/CI/test orchestration that can create branches, run checks, persist receipts, and survive demo latency
- Notes: This is over-scoped for the deadline. The causal-inference framing is likely to collapse into a scripted dashboard unless the ablation machinery is real, and real ablation is hard to define defensibly in five days. It also has a wide failure surface: Git operations, tests, approval state, model labeling, metric comparison, and receipt generation. Kill or reduce to a developer-tool receipt generator without causal claims.

## mut-r4-01-erratacommit-lab
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: A failing-before and passing-after command transcript tied to an actual repo patch and regression fixture.
- Min demo loop: One seeded broken lab instruction, one report, one replayed failure, one Codex-applied patch, one passing rerun, and one committed errata record.
- Dependencies: Reliable sandboxed command replay for the selected lab repo, GPT-5.6 access with enough quota for repeated issue-to-invariant attempts, A deliberately small fixture where the expected correction is objectively testable
- Notes: Feasible if scoped to one toy repo and deterministic commands. The 10-defect claim is too large for the deadline; judge against one or two high-quality seeded defects.

## mut-r4-02-nextstep-clerk
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: Correctly selecting one bounded next action from messy intake evidence under explicit policy constraints.
- Min demo loop: Five synthetic blocked cases, a deterministic ruleset, GPT-5.6 action recommendation, human approve/edit step, and exported task receipt.
- Dependencies: Realistic intake policy fixture with unambiguous approval rules, Calendar/task integration or credible local export path, Domain validation that selected actions are safe and compliant
- Notes: The workflow needs clinic/community-service policy expertise and risks becoming a generic task generator. Without real policy constraints, the core safety claim is mostly theatrical.

## mut-r4-03-labguard-transition-receipt
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: Intercepting an unsafe transition before execution based on executable checks and explicit invariants.
- Min demo loop: One simulated lab script, three simple invariants, one unsafe parameter change blocked before run, one safe patch allowed, and a receipt with command evidence.
- Dependencies: Machine-checkable lab safety invariants that are narrow and defensible, A sandbox runner that actually prevents execution, not just reports after the fact, Subject-matter review for any robotics, chemistry, actuator, or dosage framing
- Notes: High safety and SME burden. The 40-case and 90/95% claims are not credible for a hackathon. It can survive only if reframed as a toy simulator policy guard, not real lab safety.

## mut-r4-04-regressionpatch-drill
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: A generated regression test that fails on baseline, passes on the fix, and fails again when the model-dependent hunk is removed.
- Min demo loop: One synthetic issue, one generated failing test, one minimal patch, three command runs, and a receipt containing the exact transcripts.
- Dependencies: A small repo fixture with fast deterministic tests, Robust branch/worktree isolation for baseline, patched, and ablated runs, GPT-5.6 output constrained enough to generate useful test intent without manual rescue
- Notes: One of the stronger candidates. The ablation runner is the risky part; keep the target repo tiny and avoid arbitrary-language support.

## mut-r4-06-conflictset-review-opener
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: Computing a conflict set that is smaller than the full branch while preserving all known failing requirements and disputed claims.
- Min demo loop: One noisy seeded branch, known conflict labels, collected test/diff/claim traces, GPT-5.6 minimization, and a generated review task verified against the oracle.
- Dependencies: A seeded conflict oracle proving the minimized set still covers every conflict, Reliable extraction of claims, diffs, comments, and failing checks from one repo fixture, Clear judge-visible definition of minimality
- Notes: The minimal hitting set claim is hard to prove and easy to fake. Integration surface across GitHub comments, tests, README claims, and Devpost obligations is too broad for reliable delivery.

## mut-r4-07-traceledger-lesson-release
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: An append-only ledger where every learner-facing claim links to a source file, command transcript, artifact hash, and actor label.
- Min demo loop: One lesson with several seeded claims, scanner output, command transcript hashes, GPT-5.6 claim-to-evidence mapping, ledger writeback, and blocked-to-verified release status.
- Dependencies: A small lesson repo with claims that can be parsed and checked deterministically, Stable artifact hashing and transcript capture, A strict ledger schema that avoids vague provenance rows
- Notes: Feasible if treated as provenance instrumentation for a tiny fixture. The external repo/data-source references are inconsistent, so lock one local fixture and document licensing.

## mut-r4-08-shiftmirror-counterfactual-s
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: Producing baseline, assisted, and ablated schedules evaluated by the same constraint engine with reproducible metric deltas.
- Min demo loop: One fixed 30-shift synthetic rota, deterministic metric runner, one GPT-5.6-assisted swap proposal, one ablated comparison, and approved CSV export.
- Dependencies: A valid scheduling constraint model with availability, coverage, fairness, and overtime rules, Optimization or search logic that reliably improves the rota, Approval/export flow that avoids implying real clinical deployment readiness
- Notes: Scheduling optimization plus counterfactual attribution is too much unless heavily scripted. Data-source references are inconsistent, and domain stakes make weak constraints look careless.
