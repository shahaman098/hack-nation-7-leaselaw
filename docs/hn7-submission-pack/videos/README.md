# Hack Nation 7 — three submission videos

Track 02 asks for **Team**, **Demo**, and **Technical** uploads (HackOS + Google Form).  
**You** upload the final MP4 files:

| File | Label on HackOS | Length |
|------|-----------------|--------|
| `out/final/hn7-team.mp4` | Team | ~36s |
| `out/final/hn7-demo.mp4` | Demo | ~69s |
| `out/final/hn7-technical.mp4` | Technical | ~74s |

Live demo URL: https://leaselaw-navigator.onrender.com (recordings drive the live site).

---

## How the videos are made

1. **Voice:** `narrations/{team,demo,technical}.txt` → ElevenLabs (your cloned voice) via the
   `with-timestamps` endpoint, which also returns per-character timing (`out/audio/<track>.alignment.json`).
2. **Screen:** `record_cursor.mjs` drives headless Chromium on the live site with a visible cursor
   (eased moves, click ripple, real clicks/typing). Every action waits for a phrase in the narration,
   so the cursor lands on what the voice is describing.
   - Technical video: terminal output is captured from the real commands at record time
     (`python3 -m src.eval_harness` must exit 0 or recording aborts); GitHub is preloaded in a
     second tab and spliced in.
3. **Mux:** `assemble.sh` trims each capture to the moment narration starts and encodes 1920×1080 H.264.

---

## Step 1 — ElevenLabs env (once)

```bash
export ELEVENLABS_API_KEY="your_key"
export ELEVENLABS_VOICE_ID="your_voice_id"
```

Do not commit keys. Rotate if pasted in chat.

---

## Step 2 — Full pipeline

```bash
cd /Users/efi/Hackathons/Hack-Nation-7/apps/leaselaw/scripts/video
bash run_all.sh
```

Or step by step:

```bash
cd apps/leaselaw/scripts/video
python3 generate_voiceover.py --all --timestamps     # only needed after editing narrations
npm install && npx playwright install chromium
node record_cursor.mjs all                           # or: team | demo | technical (real time, ~4 min total)
bash assemble.sh                                     # or: bash assemble.sh demo
```

Debug a scene quickly (no waiting on narration, logs every click target):

```bash
FAST=1 DEBUG=1 node record_cursor.mjs demo
```

---

## Edit narrations

Edit `narrations/*.txt`, regenerate with `--timestamps`, then re-record. Cues in `record_cursor.mjs`
reference exact phrases (`d.cue("I click Check my address")`); if you reword a cued phrase, update
the matching cue or the recorder stops with "phrase not in narration".

Superseded experiments (not used by `run_all.sh`): `record_beats.mjs`, `beat_actions.mjs`, `beats/*.json`,
and the old fixed-sleep `record_demo.mjs` / `record_technical.mjs` / `record_team_slides.mjs`.
