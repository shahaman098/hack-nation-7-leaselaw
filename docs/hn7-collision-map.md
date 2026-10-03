# Hack-Nation 7 — Collision map (solo, podium-first)

**VERIFIED:** Official must-ship from PDFs · `docs/hn7-official-rubric.md`  
**VERIFIED:** HackForge `crowded-archetypes.json` + `winner-patterns.json` · run `2026-10-03-hack-nation-7-kickoff`  
**ESTIMATE:** Crowd this weekend from track incentives + past ElevenLabs / Hack-Nation patterns

---

## Per-track crowd vs wedge

### 01 — ElevenLabs AI Apprentice

| Crowded | Underexplored / differentiate |
|---------|-------------------------------|
| Generic “voice meeting notes” | Timed why-Qs tied to **screen events** |
| Chatbot that summarizes a recording | Work Map with **guardrails + expert words** |
| Tutor that reads a static FAQ | Tutor that **stops a wrong decision** on an unseen case |

**Do not build:** Recorder-without-why; transcript summary as “debrief”; tutor that never watches the new hire’s screen.

**HackForge concepts:** WhyWindow / MapConflict sit in the right family but still need **all three modules** (Capture/Map/Teach) per PDF — scheduling polish is optional; screen+voice is not.

---

### 02 — RealPage Housing Law Navigator

| Crowded | Underexplored / differentiate |
|---------|-------------------------------|
| “Chat with housing PDFs” | **Automated extraction** into schema + score.py |
| Generic RAG without jurisdiction stack | Address → state/county/city + coverage conditions |
| Ignoring pending vs enacted | Change tests T1–T6 + hour-16 ordinance |

**Do not build:** Hand-authored rules only (fails automated extraction + hour-16 check); inventing citations; “legal advice” framing.

**HackForge note:** Pure “appeal pathway” alone is **not** enough — must still ship Modules A/B/C and JSON outputs. Appeal/procedure UX can be a **UI wedge** on top of the scored pipeline, not a substitute.

**Advantage:** **75% auto-scored** → solo can optimize against `score.py` + dev key instead of voice polish wars.

---

### 03 — Databricks Agentic Discovery

| Crowded | Underexplored |
|---------|---------------|
| Multi-agent “roleplay” without experiment | Real Omnigent handoffs + result that **changes next experiment** |
| Local-only loop labeled Databricks | Managed Databricks Omnigent **or** OSS Omnigent with proof |

**Do not build:** Decorative Databricks (HackForge red-team kill on Replication Arena).

---

### 04a–c — World Bank Small AI

| Crowded | Underexplored |
|---------|---------------|
| Generic symptom / chatbot | Offline-first SMS/voice on real devices + sector annex data |
| Cloud-only LLM demo | Explicit connectivity / language constraints |

**Constraint:** Youth eligibility **18–35**; Seoul prize is travel, not cash ladder.

---

### 05 — Rare Disease Atlas

| Crowded | Underexplored |
|---------|---------------|
| Pretty graph with no citations | Every edge sourced; honest “no route” |
| Disease directory UI | Mechanism clustering + **patient next step this week** |

**Do not build:** Static directory; OpenAI-free entry if chasing track prizes (PDF: OpenAI required for track prizes).

---

## Expected weekend archetypes (estimate)

1. **Many Track 01** entries chasing ElevenLabs prizes — voice quality high, incomplete Teach module common.
2. **Many Track 02** RAG chatbots that **fail score.py** — opportunity if you treat scoring as the product.
3. **Track 03** Omnigent theater without measurable learning.
4. **Track 05** pretty graphs without patient action.

---

## Solo differentiation rule

Ship the **non-fakeable proof** the PDF names, then add one visible wedge:

- Track 02: max auto score → then plain-language renter view + conflict flags.  
- Track 01: three modules on one workflow → then MapConflict stretch.  
- Avoid tracks where the mandatory platform (Omnigent / full screen-voice-tutor) is the whole weekend for a solo builder unless you already have that stack warm.
