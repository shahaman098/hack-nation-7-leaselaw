#!/usr/bin/env bash
# Voice (ElevenLabs, with timings) → cursor-driven screen capture → MP4s.
set -euo pipefail
cd "$(dirname "$0")"
REPO="$(cd ../../../.. && pwd)"

if [[ -z "${ELEVENLABS_API_KEY:-}" || -z "${ELEVENLABS_VOICE_ID:-}" ]]; then
  echo "Export ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID first." >&2
  echo "See $REPO/docs/hn7-submission-pack/videos/README.md" >&2
  exit 1
fi

export LIVE_URL="${LIVE_URL:-https://leaselaw-navigator.onrender.com}"

python3 generate_voiceover.py --all --timestamps
npm install
npx playwright install chromium
node record_cursor.mjs all
bash assemble.sh
