# Hack-Nation 7 — Official rubric (from challenge PDFs)

**VERIFIED:** PDFs downloaded from HackOS `api/documents/*` → signed Supabase URLs · `pdftotext` · 2026-10-03  
**VERIFIED:** Prizes + credits from HackOS UI · browser CDP  
**Sources:** `briefs/hack-nation-7-pdfs/*.pdf` · extracts in `briefs/hack-nation-7-pdf-extracts/`

Shared submission (HackOS + AGB): GitHub repo, live deployment, **three videos**, HackOS project + [Google Form](https://forms.gle/VS65tsovASMuBwEn9). Team 1–4. Deadline **4 Oct 2026 14:00 BST** (+15 min upload grace).

Video labels (RealPage PDF + HackOS pattern): **Team** · **Demo** · **Technical**. RealPage additionally requires **score.py** report on screen.

---

## Track scoring table

| Track | Must-ship | Nice-to-have | Sponsor signals | Solo complexity (1–5) | Judging shape |
|-------|-----------|--------------|-----------------|----------------------|---------------|
| **01 ElevenLabs** | Capture (screen + voice why-Qs) + Map (debrief → Work Map) + Teach (voice tutor on new hire screen). ≥3 live Qs, ≥1 guardrail; debrief ≥3 follow-ups + teach-back; tutor catches wrong decision on unseen case | Dual expert, multilingual, agent-ready export | **ElevenLabs required in path** (ElevenAgents, Scribe, Expressive). Credits: Creator tier on HackOS | **5** | Qualitative “what good looks like”; Apprentice Test (5 Qs). No numeric rubric in PDF |
| **02 RealPage** | Modules A+B min (extraction + address lookup); C change tracking for full score. Outputs: `rules.json`, `lookups.json`, `changes.json`. Automated extraction only. “Unknown” OK. “Not legal advice” | ES/EN UI, confidence, live new jurisdiction | **Starter pack + score.py** (Drive). 75 pts auto / 25 judges | **3** | **100 pts:** Extraction 25 · Address 20 · Citations 15 · Change 15 · UX 10 · Responsible 10 · Scale 5 |
| **03 Databricks** | **Omnigent mandatory** orchestration; multi-agent discovery loop; experiment that changes next decision | Wet-lab next step (not required) | Omnigent on Databricks **or** open-source Omnigent | **4** | **30% Omnigent · 25% breakthrough · 20% acceleration · 15% rigor · 10% creativity** |
| **04a/b/c World Bank** | Offline/constrained Small AI for **one** sector (Health / Ag / Tourism); local language/device story; datasets from brief | Seoul Ignite Talk for sector winners | Same PDF for all three sectors (annex differs) | **4** | 25% Small AI fidelity · 20% impact · 15% data · 15% evidence · 15% clarity · 10% scale · RAI pass/fail. **Age 18–35** |
| **05 Buffalo × OpenAI** | Evidence-backed KG + explainable edges + patient next step | New experiment proposals | **OpenAI models required for track prizes** | **4** | Graph quality · Evidence integrity · Patient progress · 10× impact · Craft (no weights) |

---

## Credits (HackOS, verified)

| Credit | Status (this account) | Notes |
|--------|----------------------|--------|
| Anthropic $25 | **Claimed** | Offer link present |
| BrightData $300 | **Claimed** | Code `hacknation26` |
| ElevenLabs Creator (1 mo) | Available | Claim for Track 01 |
| Lovable Pro (1 mo) | Available | Optional UI |
| Databricks / Omnigent | Not listed under Credits | Track 03 uses login / OSS Omnigent |

---

## Prizes (HackOS, verified)

| Scope | Reward |
|-------|--------|
| Overall | Venture Lab Fast Track + $2,000 Anthropic; top 2/challenge pitch Sat Oct 10 |
| 01 ElevenLabs | 1st $500 + Scale plan; 2nd/3rd cash + plans |
| 02 RealPage | 1st $500 + $2k Anthropic; 2nd/3rd cash + credits |
| 03 Databricks | Same cash/credit ladder as RealPage |
| 04 World Bank | Seoul trip (~$2k) per sector winner |
| 05 Buffalo | OpenAI credits $10k / $5k / $2k |
| Side awards | Creativity / Best Quote / Go Viral ($500 Anthropic each) |

---

## RealPage starter pack

- Drive: https://drive.google.com/drive/folders/14TT6AEH8TStzoT5c5fZ45Bt4grODsowR  
- Local mirror target: `briefs/hack-nation-7-realpage-starter/`  
- Hour-16 fictional ordinance released mid-event in the same Drive folder.
- **UNKNOWN / partial:** `gdown` hit Drive rate-limit / permission errors mid-folder; finish download manually in browser (Download folder) if `score.py` / schema / addresses CSV are missing locally.

---

## Document IDs (HackOS)

| Track | Document UUID |
|-------|---------------|
| 01 | `4e5b3285-ab97-4f53-bdcc-fa6a9dd1d932` |
| 02 | `553bf520-c213-4a98-81a0-6bc85a2fa773` |
| 03 | `c0bdd796-5a59-4550-b36a-f4f223ce1409` |
| 04a | `eb3ffdbd-c394-4b7d-8791-9cdb80439a5d` |
| 04b | `365bf016-025f-45b4-93e4-206816cd7dfa` |
| 04c | `788d5777-be9d-4b8f-9f56-756bede7090e` |
| 05 | `385c870d-0017-462e-9a3f-8db43a9556bf` |

**Note:** 04a/b/c PDFs are **byte-identical** (same concept note; sector annexes inside).
