# Video script — LeaseLaw

## Team (≤60s)

Solo track · LeaseLaw Navigator · Track 02 RealPage · automated corpus extract + deterministic as-of engine.

## Demo (≤90s)

Follow `docs/hn7-submission-pack/README.md` demo script. Show eval T1–T5 pass on screen.

## Technical (≤120s)

1. Corpus → `extract_rules.py` → official schema `rules.json` with `quoted_span`.  
2. `jurisdiction.py` maps Boston neighborhoods → legal city.  
3. `engine.py` evaluates coverage + effective dates + supersession.  
4. `export_outputs.py` builds lookups for 500 addresses + changes T1–T5.  
5. FastAPI UI for judge walkthrough.
