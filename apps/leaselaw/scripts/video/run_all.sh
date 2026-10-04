#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"

if [[ -z "${ELEVENLABS_API_KEY:-}" || -z "${ELEVENLABS_VOICE_ID:-}" ]]; then
  echo "Export ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID first." >&2
  echo "See $REPO/../docs/hn7-submission-pack/videos/README.md" >&2
  exit 1
fi

python3 generate_voiceover.py --all
npm install
npx playwright install chromium
LIVE_URL="${LIVE_URL:-https://leaselaw-navigator.onrender.com}" node record_demo.mjs
LIVE_URL="${LIVE_URL:-https://leaselaw-navigator.onrender.com}" node record_technical.mjs
LIVE_URL="${LIVE_URL:-https://leaselaw-navigator.onrender.com}" node record_team_slides.mjs
bash assemble.sh
