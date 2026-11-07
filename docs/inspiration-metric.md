# Inspiration metric

HackForge scores **finalists** against a curated corpus of verified prior winners (`corpora/verified-winners/seed.jsonl`). This is separate from public-project **collision** evidence.

## Dimensions

For each finalist and winner record we compute token Jaccard alignment on:

1. **user_alignment** — `primary_user` vs winner `primary_user`
2. **problem_alignment** — `painful_workflow` vs winner `problem`
3. **mechanism_alignment** — `imported_mechanism` vs winner `mechanism`

The **aggregate score** is the arithmetic mean of the three dimensions.

## Thresholds

| Variable | Default | Meaning |
|----------|---------|---------|
| `HACKFORGE_INSPIRATION_MIN` | `0.30` | Flag when aggregate ≥ threshold |
| `HACKFORGE_INSPIRATION_CLONE_DIM` | `0.72` | Clone guard when **all three** dimensions ≥ this value |
| `HACKFORGE_TRAINING_CUTOFF` | unset | ISO date; winners after cutoff are excluded from pattern mining and scoring corpus |

## Outputs

- `winner-patterns.json` — mined archetypes/mechanisms/demo patterns fed into ideation after competition research
- `inspiration-report.json` — per-finalist nearest winners, flags, and clone-guard notes

Clone-guard hits are recorded in run rejections for audit; they do not silently rewrite judge outputs.
