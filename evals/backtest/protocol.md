# Winner-backtest protocol (frozen before live runs)

Decision: pipeline recall@3 must strictly beat shuffled-pool, fixture-naive,
and live-naive controls on verified post-cutoff cases. Otherwise rework judging
before adding pipeline sophistication. Fixture runs never satisfy this gate.

Ranking: final outputs in manifest order; remaining judged candidates by official
criteria score; collision survivors; remaining gate-passed concepts by external
quality; killed/failed candidates last. All raw concepts occur exactly once.

Matcher: user/problem/mechanism content-token Jaccard, threshold 0.30, with
0.20/0.30/0.40 sensitivity. Optional embedding scorer explicitly requires the
existing collision extras. This is a lexical/semantic proxy, not a human verdict.
Use the same matcher and threshold for every arm. Never tune to observed winners.

Leakage: no live research; own winner titles and URLs removed from retrieved
collision analogues before prompts, including repair paths. Exact winner-title
reuse is reported. Cutoff must be documented for the selected model; unknown
cutoff cases cannot satisfy the post-cutoff decision gate.

Live runs require --live and --max-cases and fail on the first error. Backend
caps are retained. Runs live outside runs/ and manifests say source=backtest.
One live-naive call per case is the only additional inference for evaluation.

Real cases lacking confirmed winner lists are deliberately blocked, not replaced
by synthetic winners or historical pipeline recommendations.

Implementation-sequencing amendment: the user explicitly authorized implementing
Phase 2 while the real backtest remains inconclusive. The empirical decision rule
above is unchanged. Backtest ranking runs pass build_plan=False to preserve their
original inference budget and isolate the ranking experiment.
