# LeaseLaw — agent notes (scoped)

Parent contract: repo-root [`AGENTS.md`](../../AGENTS.md) + [`docs/OPS_RUNBOOK.md`](../../docs/OPS_RUNBOOK.md) + [`docs/WIN_BOARD.md`](../../docs/WIN_BOARD.md).

## Product one-liner

Address + as-of date → applicable rental housing rules with citations/quotes (Track 02 RealPage). **Not legal advice.**

## Module map

| File | Role |
|------|------|
| `src/paths.py` | Starter pack root |
| `src/data.py` | Load addresses/rules/corpus |
| `src/jurisdiction.py` | `legal_city` (MA neighborhoods → Boston) |
| `src/extract_rules.py` | Automated corpus → official schema rules |
| `src/extractors/city_extra.py` | Extra city rules (merge in `extract_all`) |
| `src/engine.py` | Evaluate applies / pending / not_yet_effective / superseded |
| `src/export_outputs.py` | Write `out/rules|lookups|changes.json` |
| `src/eval_harness.py` | Official change tests T1–T5 |
| `src/main.py` | FastAPI + demo UI + `/api/eval` score panel |

## Verify

```bash
python -m src.eval_harness
curl -s localhost:8012/api/eval
curl -s localhost:8012/health
```

## Port

**8012** (do not silently change).
