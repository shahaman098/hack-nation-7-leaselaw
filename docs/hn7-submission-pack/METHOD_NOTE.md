# LeaseLaw Navigator — one-page method note

**Hack-Nation 7 · Track 02 RealPage · Not legal advice.**

## Question

For a sample multifamily address and an **as-of date**, which public housing rules apply, with citations and traceable source text?

## Pipeline (Modules A–C)

1. **Extract (A)** — `src/llm_extract.py` + `src/corpus_automate.py` scan all `corpus/text/*.txt` documents listed `status=ok` in the manifest. Each candidate rule must pass a **deterministic verifier**: `quoted_span` is a literal substring of the source file (`src/verify.py`). Canonical ids for change tests T1–T5 are preserved via `extract_core` needles. Optional Anthropic pass writes to `out/llm_cache/`; deploy uses `--offline` replay. Audit: `out/audit/extraction_log.jsonl`.

2. **Resolve (B)** — `src/jurisdiction.py` maps mailing cities (Boston neighborhoods, San Ysidro → San Diego) and county; optional Census batch cache (`src/geocode.py`). `src/engine.py` tests structured coverage (`out/rule_coverage.json`): certificate-of-occupancy cutoffs, rolling AB 1482 age, missing units → **`unknown`**, owner exemptions → **`unknown`**. Supersession uses rule `overrides` / interaction (local rent control over state cap).

3. **Change track (C)** — `src/eval_harness.py` runs T1–T5 on all 500 addresses. Exports: `out/rules.json`, template-shaped `out/lookups.json`, `out/changes.json` (rich debug under `out/debug/`).

## Responsible design

- Enacted / pending / not-yet-effective / **failed** separated; failed ballot MA rent cap never reported as applying.
- **Conflict flags** for FAIR preemption, Berkeley dual effective dates, and other pack §9 open questions.
- Every API/UI response includes disclaimer; `/api/audit/{id}` shows reasoning trace + retrieval date.

## Limits

- Hoboken / Jersey City **algorithmic** ordinances: corpus is link-only or non-matching text — rules `HOB-ALG-01` / `JC-ALG-01` are labelled evidence gaps (low confidence).
- Parcel data lacks owner names and often unit counts / exact certificate dates → intentional `unknown`.

## Reproduce

```bash
cd apps/leaselaw && ./scripts/reproduce.sh
```

## Live demo

Durable host: Render (`render.yaml` at repo root). Health: `GET /health`, scorecard: `GET /api/eval`.
