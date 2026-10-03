# Implementation and experiment status

- Phase 0 completed in commits `46f4581` and `3a99638`; archive files remain on disk.
- Phase 1 harness implemented with ranking, matching, three control arms,
  sensitivity, cutoff splits, leakage filtering and offline integration tests.
- Official winner lists verified for OpenAI Build Week (eight winner ribbons),
  TxODDS (nine podium projects) and fal × Sequoia (first place only — the only
  placement organizers ever published; documented denominator caveat in
  `cases.json`). Three cases remain unverified: HackNation (two of six first-place
  winners lack any describable source: Vera AI undescribed, Amira mechanism
  unknown) and UK Parliament/EasyA (no public winner list exists; see
  `winner-verification.md`).
- Generator model and cutoff now documented (2026-10-03): all live backtests pin
  `HACKFORGE_CODEX_MODEL=gpt-5.6-sol`; its knowledge cutoff (Feb 16, 2026) was
  read from the official per-model docs page
  `https://developers.openai.com/api/docs/models/gpt-5.6-sol` (fetched). The
  account rejects `gpt-6.1-sol` ("not supported with a ChatGPT account"), so the
  pinned default is the only documented-cutoff generator available. All five real
  events are after the cutoff: every real case is `cutoff_class: post-cutoff`
  with a `cutoff_note`. The former `verification-research.md` was removed from
  the working tree by a concurrent edit; its cutoff evidence is consolidated in
  `winner-verification.md`.
- One-case live smoke (`openai-build-week`, Codex) launched 2026-10-03; the full
  three-case live batch follows on success. Earlier fixture verdict
  `insufficient_data` remains the standing verdict until the live batch lands.
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
