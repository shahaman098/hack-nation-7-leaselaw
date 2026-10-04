#!/usr/bin/env bash
# Mux ElevenLabs MP3 + Playwright WebM → submission MP4
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
BASE="$REPO/docs/hn7-submission-pack/videos/out"
AUDIO="$BASE/audio"
SCREEN="$BASE/screen"
FINAL="$BASE/final"
mkdir -p "$FINAL"

mux() {
  local name="$1"
  local webm="$SCREEN/${name}.webm"
  local mp3="$AUDIO/${name}.mp3"
  local mp4="$FINAL/hn7-${name}.mp4"
  if [[ ! -f "$webm" ]]; then
    echo "Missing screen: $webm (run record_*.mjs first)" >&2
    return 1
  fi
  if [[ ! -f "$mp3" ]]; then
    echo "Missing audio: $mp3 (run generate_voiceover.py first)" >&2
    return 1
  fi
  ffmpeg -y -i "$webm" -i "$mp3" \
    -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p \
    -c:a aac -b:a 192k \
    -shortest "$mp4"
  echo "VERIFIED: $mp4 · duration · $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$mp4")s"
}

for track in team demo technical; do
  mux "$track"
done

echo "Upload files in $FINAL to HackOS."
