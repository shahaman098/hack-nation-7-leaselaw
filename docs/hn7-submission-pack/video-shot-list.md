# Three videos — Track 02 RealPage

Labels from RealPage PDF + HackOS: **Team** · **Demo** · **Technical**.

## 1) Team (~60–90s)

- Name, solo / Brunel, Track 02 RealPage
- One line problem: address-level housing law is layered and changing
- One line approach: extract → resolve → cite → track change
- Why TrustRAG / citations matter

## 2) Demo (~2–3 min) — **must show scores**

1. Live URL + “Not legal advice”
2. SF address as-of 2025-12-31 → AB325 not yet effective
3. Toggle 2026-01-02 → applies; SF local supersedes state rent cap
4. Boston → no invented rent cap; pending stays pending
5. Terminal: `python score.py` (official) **or** fixture `eval_harness.py` until starter lands — show full report
6. Mention hour-16 ordinance readiness

## 3) Technical (~2–3 min)

- Corpus → rule schema (automated extraction plan)
- Jurisdiction stack + coverage conditions
- As-of engine + supersession
- Output files for judges
- Limitations: fixture vs full 500-address run; unknown when facts missing
