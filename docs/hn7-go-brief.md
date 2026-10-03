# HN7 go brief — Track 02 RealPage (recommended)

**Decision:** **A — Track 02** (solo, podium-first)  
**Working title:** LeaseLaw Navigator  
**Evidence:** `docs/hn7-decision-matrix.md` · spike `spikes/track02-realpage/` PASS 5/5

---

## Killer demo (90 seconds)

1. Open live app → disclaimer “Not legal advice.”
2. Address **SF sample** · as-of **2025-12-31** → AB325 / algorithmic rule = **not yet effective** (citation + quote).
3. Toggle as-of **2026-01-02** → same rule **applies**; show local SF rent ordinance **supersedes** AB1482.
4. Switch to **Boston** address → **no local rent cap**; pending MA bill stays **pending**.
5. Run `score.py` on **dev key** → show full score report on screen (required in videos).
6. (If hour-16 dropped) ingest fictional Cambridge ordinance live → new `changes.json` rows.

---

## Must ship (PDF)

| Artifact | Notes |
|----------|--------|
| `rules.json` | Automated extraction from corpus |
| `lookups.json` | All ~500 addresses |
| `changes.json` | T1–T6 (+ hour-16) |
| Live URL + GitHub | README with run + score |
| Videos | Team · Demo · Technical; **include scores** |
| Google Form + HackOS | Dual submit |

---

## Cut list

- Full US law coverage  
- Appeal/notice writer as core (optional stretch UI only)  
- Voice / ElevenLabs  
- Databricks / Omnigent  

---

## Stack

- FastAPI + thin Next/React or server-rendered UI  
- LLM extraction (Anthropic credits already claimed)  
- Census geocoder for jurisdiction stack  
- Deterministic coverage engine (year built, units, as-of)  
- Bundle RealPage starter from Drive folder `14TT6AEH8TStzoT5c5fZ45Bt4grODsowR`

---

## Starter pack status

**VERIFIED:** Unpacked at `briefs/hack-nation-7-realpage-starter/participant-final-no-hour16 3/` · 500 addresses · 54 corpus texts · schema + T1–T5 · **no score.py** in this “no-scoring” pack · LeaseLaw `/health` loads pack.

## Immediate human actions

1. Create HackOS team (solo).  
2. Select challenge **02 RealPage**.  
3. You submit HackOS + Google Form + videos (agent prepares pack only).

---

## Backup if blocked

If starter pack / score.py inaccessible: pivot **B — Track 01 MapConflict** with ElevenLabs credit claim; spike already green.
