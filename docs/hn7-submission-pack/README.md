# HN7 submission pack — LeaseLaw (Track 02)

## Product

- **Name:** LeaseLaw Navigator  
- **Track:** 02 RealPage  
- **Repo path:** `apps/leaselaw/`  
- **Local demo:** `http://127.0.0.1:8012`  
- **Live tunnel (ephemeral):** `https://comparing-providers-disciplines-foreign.trycloudflare.com` (see also `LIVE_URL.txt`)  
- **Disclaimer:** Not legal advice.

## Artifacts (generate before recording)

```bash
cd apps/leaselaw
python -m src.extract_rules
python -m src.export_outputs
python -m src.eval_harness   # must show T1–T5 pass
```

| File | Path |
|------|------|
| rules | `apps/leaselaw/out/rules.json` |
| lookups | `apps/leaselaw/out/lookups.json` |
| changes | `apps/leaselaw/out/changes.json` |
| eval | `apps/leaselaw/out/eval-report.json` |

## Demo script (90s)

1. Open live URL → show **Not legal advice.**  
2. SF address · as-of **2025-12-31** → `CA-ALG-01` = `not_yet_effective`.  
3. Toggle **AB325 before/after** → after **2026-01-02** = `applies`.  
4. Hoboken vs Newark → local alg ban only on Hoboken.  
5. Boston/Cambridge → MA bills `pending`; no rent cap applies.  
6. Show `out/eval-report.json` T1–T5 all pass (stand-in until `score.py`).

## Human checklist (you click)

- [ ] HackOS team (solo)  
- [ ] Select challenge **02 RealPage**  
- [ ] Dual submit: HackOS + Google Form  
- [ ] Upload Team / Demo / Technical videos  
- [ ] Paste GitHub + live URL  

Agents do **not** submit.
