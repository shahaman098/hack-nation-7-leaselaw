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
- Phase 2 build-plan integration remains **not implemented**, honoring the agreed
  phase order and empirical gate. It must not be described as completed.

To resume: install the project's existing optional collision extras and cache its
configured embedding model, obtain organizer-backed winner lists for the remaining
three cases, and document the selected generator's cutoff. Run a new one-case
live smoke and then the full batch. If post-cutoff recall@3 fails to beat every
control, rework judging rather than proceeding to build-plan sophistication.

Verification: `make lint typecheck test-fast` passes locally (76 tests, two slow
tests deselected). Remote CI and its Python 3.9/3.11/3.12 matrix were not run.
