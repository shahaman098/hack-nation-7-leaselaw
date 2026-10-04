# Hack Nation 7 — three submission videos

Track 02 asks for **Team**, **Demo**, and **Technical** uploads (HackOS + Google Form).  
**You** upload the final MP4 files. This folder holds scripts and automation.

Live demo URL: https://leaselaw-navigator.onrender.com  
(LIVE_URL.txt at repo root of submission pack.)

---

## Step 1 — Clone your voice in ElevenLabs (once)

1. Sign in at [elevenlabs.io](https://elevenlabs.io) (Hack Nation Creator tier if you claimed it).
2. **Voices → Add voice → Instant Voice Clone** (or Professional if you have samples).
3. Upload **1–3 minutes** of your speech (clear mic, no music). Use your normal speaking voice.
4. Name it e.g. `aman-hn7`.
5. Open the voice → copy **Voice ID** (32-char hex).
6. **Profile → API Keys** → create key.

In Cursor terminal:

```bash
export ELEVENLABS_API_KEY="your_key"
export ELEVENLABS_VOICE_ID="your_voice_id"
```

Optional: model (default `eleven_multilingual_v2`):

```bash
export ELEVENLABS_MODEL_ID="eleven_multilingual_v2"
```

---

## Step 2 — Generate voiceovers (your voice only)

```bash
cd /Users/efi/Hackathons/Hack-Nation-7/apps/leaselaw
pip install requests   # if needed
python3 scripts/video/generate_voiceover.py --all
```

Outputs:

- `docs/hn7-submission-pack/videos/out/audio/team.mp3`
- `docs/hn7-submission-pack/videos/out/audio/demo.mp3`
- `docs/hn7-submission-pack/videos/out/audio/technical.mp3`

---

## Step 3 — Record screen (no mic; video only)

```bash
cd apps/leaselaw/scripts/video
npm install
npx playwright install chromium
LIVE_URL=https://leaselaw-navigator.onrender.com node record_demo.mjs
node record_technical.mjs
node record_team_slides.mjs
```

Raw WebM files land in `docs/hn7-submission-pack/videos/out/screen/`.

**Tip:** Wake Render first (open the live URL in a tab, wait ~60s if it slept).

---

## Step 4 — Mux voice + video

```bash
cd /Users/efi/Hackathons/Hack-Nation-7/apps/leaselaw
bash scripts/video/assemble.sh
```

Final files (upload these):

| File | Label on HackOS |
|------|-----------------|
| `videos/out/final/hn7-team.mp4` | Team |
| `videos/out/final/hn7-demo.mp4` | Demo |
| `videos/out/final/hn7-technical.mp4` | Technical |

Verify:

```bash
for f in docs/hn7-submission-pack/videos/out/final/*.mp4; do
  ffprobe -v error -show_entries format=duration -of default=nw=1 "$f"
done
```

---

## One command (after Step 1 env vars)

```bash
cd apps/leaselaw && bash scripts/video/run_all.sh
```

---

## What each video shows (matches current UI)

- **Team:** Logo + bullet slides + your ElevenLabs voice (no score panel on home; that is intentional).
- **Demo:** Live site, example buttons, Spanish toggle, How we decided, `eval-report.json` with passed 5.
- **Technical:** About page, terminal harness, optional code scroll.

Narration text is in `narrations/*.txt`. Edit there, re-run generate + assemble.
