# Implementation and experiment status

- Phase 0 completed in commits `46f4581` and `3a99638`; archive files remain on disk.
- Phase 1 harness implemented with ranking, matching, three control arms,
  sensitivity, cutoff splits, leakage filtering and offline integration tests.
- Official winner lists verified for OpenAI Build Week (eight winner ribbons)
  and TxODDS (nine podium projects). Three other lists are still unverified.
- No generator model training cutoff is documented. All five real cases are
  therefore classified **unknown**, not assumed post-cutoff based on event dates.
- The tracked fixture report is an offline harness baseline only. It has verdict
  **insufficient_data**, not a claim that rankings predict real winners.
- One exploratory Codex smoke was initiated while the protocol was written but
  before its commit. It was interrupted after discovering absent semantic-ranking
  extras; it produced no completed backtest. It must not count as a confirmatory
  experiment. New live runs preflight the missing dependency before paid calls.
- The full live batch was not run: it would fail validation for the three missing
  winner lists. The first failure stops a batch rather than silently skipping cases.
- Phase 2 implementation was explicitly authorized by the user despite the
  inconclusive backtest. The build-plan stage, schema, prompt, CLI flag and offline
  tests are now implemented. This waiver changes implementation sequencing only,
  not the empirical verdict: no real winner-prediction claim is supported.

- Existing collision extras and the configured embedding model were successfully
  preflighted in an isolated Python 3.12 `uv` environment; no new runtime
  dependencies were added to the project.
- A full live analysis of `briefs/hacknation-global-ai-2026.md`, including build
  planning, was launched in that environment. Results are pending; it is an
  execution smoke, not a winner backtest.

To finish empirical validation: obtain organizer-backed winner lists for the
remaining three cases and document the selected generator's cutoff. Run a one-case
live smoke and then the full batch. If post-cutoff recall@3 fails to beat every
control, rework judging. Build-plan availability must not be treated as evidence
that the ranking is predictive.

Lint, typecheck and all 90 fixture tests pass on Python 3.9, 3.11 and 3.12 locally
(two slow tests deselected).
Wheel/sdist builds and `twine check` passed; an isolated wheel installation ran the
complete fixture pipeline and validated its build-plan artifact. Remote CI was
not published and must not be described as green without a published run.
