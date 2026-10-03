# Hack-Nation 7 — Decision matrix (solo, podium-first)

**VERIFIED:** Official rubrics from PDFs · `docs/hn7-official-rubric.md`  
**VERIFIED:** Spike Track 02 `PASS 5/5` · `python3 spikes/track02-realpage/lookup.py`  
**VERIFIED:** Spike Track 01 MapConflict `PASS` · `python3 spikes/track01-mapconflict/mapconflict.py`  
**Goal:** maximize track podium probability for solo builder.

Weights (from plan):

```
Score = 0.30*JudgeDemoClarity + 0.25*NonFakeableProof + 0.20*PersonalFit
      + 0.15*LowCollision + 0.10*SponsorLeverage
```

Scores are 1–5 integers.

| Concept | Track | Demo | Proof | Fit | Collision | Sponsor | **Weighted** |
|---------|-------|------|-------|-----|-----------|---------|--------------|
| **RealPage scored navigator** (schema extract + lookup + change) | **02** | 5 | 5 | 5 | 4 | 5 | **4.85** |
| Appeal/procedure UI wedge on top of scored pipeline | 02 | 4 | 4 | 5 | 5 | 4 | **4.35** |
| MapConflict (narrow Why/Work Map) | 01 | 4 | 4 | 4 | 3 | 5 | **3.95** |
| WhyWindow (full scheduler+tutor) | 01 | 3 | 3 | 4 | 3 | 5 | **3.45** |
| Doorstep-only chat RAG (no score.py) | 02 | 2 | 1 | 4 | 1 | 2 | **2.00** |
| Replication Arena / Omnigent lab | 03 | 3 | 3 | 2 | 2 | 3 | **2.65** |
| Small AI offline (any 04x) | 04 | 3 | 3 | 2 | 3 | 2 | **2.70** |
| Rare Disease Atlas slice | 05 | 3 | 3 | 3 | 3 | 4 | **3.10** |

### Scoring notes

- **Track 02 wins** because the PDF publishes a **100-point rubric with 75 auto points** and a starter pack + `score.py`. Solo builders can iterate against a machine grader instead of fighting voice UX polish.
- **Personal fit:** TrustRAG / FastAPI / citations / rule-version diffs map directly to Modules A–C. AppealPath prior art is a UI/story layer, not a substitute for automated extraction.
- **Track 01** still strong if you want ElevenLabs prizes, but PDF requires **screen share + vision events + Capture/Map/Teach** — solo complexity 5. MapConflict spike proves the teach/hold loop; it does **not** yet satisfy Capture requirements.
- **Track 03** Omnigent is mandatory — red-team already killed decorative Databricks.
- **Track 05** OpenAI required for track prizes; graph surface is large for solo.
- **Track 04** age 18–35 + offline fidelity; weaker stack leverage.

---

## Recommendation

| Rank | Choice | Line for sign-off |
|------|--------|-------------------|
| **#1** | **Track 02 — RealPage scored Housing Law Navigator** | **A** (procedure/appeal as optional UI, not core) |
| **#2** | Track 01 — MapConflict / AI Apprentice | **B** |
| Reject for podium-first solo | WhyWindow full (**C**), Omnigent lab, WB offline, Rare Atlas unless #1 blocked |

**Primary product name (working):** **LeaseLaw** / **Doorstep Diff** — address in → cited applies/pending/superseded → as-of toggle → change-affected addresses.

**Cut list:** hand-authored rules without LLM extraction; chat UI without `rules.json`/`lookups.json`/`changes.json`; legal-advice claims.

---

## Sign-off line

Plan gate options: **A** Track 02 · **B** Track 01 MapConflict · **C** Track 01 WhyWindow · **D** Other.

**Research recommendation: A.**

See [hn7-go-brief.md](hn7-go-brief.md) for demo script and build cut list.
