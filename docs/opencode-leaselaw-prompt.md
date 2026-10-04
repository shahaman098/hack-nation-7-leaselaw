# OpenCode prompt — LeaseLaw (Mimo v2.6 Flash free)

Paste into OpenCode `run` (model `opencode/mimo-v2.6-flash-free`):

```
Work in /Users/efi/Hackathons/Hack-Nation-7/apps/leaselaw only.

Cursor owns extract_rules.py / engine.py / eval_harness.py — do not rewrite them.
Your job:
1) Add apps/leaselaw/src/extractors/city_extra.py that reads corpus texts under
   briefs/hack-nation-7-realpage-starter/participant-final-no-hour16 3/corpus/text/
   and returns ADDITIONAL official-schema rules for Berkeley (D001), San Diego (D076),
   San Francisco algorithmic ban (D081), LA just-cause/RSO if clearly supported.
   Each rule MUST include a real quoted_span substring copied from the corpus file
   and correct source_doc_id / source_url from corpus_manifest.csv.
2) Wire city_extra into extract_rules.extract_all() if that function exists and
   merges lists; otherwise write out/extra_rules.json and stop.
3) Light polish of the HTML in main.py (keep "Not legal advice", keep demo toggle).
4) Do not deploy, push, or submit anything.

Verify: python -m src.extract_rules && python -m src.eval_harness
```
