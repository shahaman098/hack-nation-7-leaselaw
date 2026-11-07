#!/usr/bin/env bash
# Mux ElevenLabs narration + cursor screen capture → submission MP4s.
#   bash assemble.sh            # all three
#   bash assemble.sh demo       # one track
# Cut points come from out/screen/<track>.json (written by record_cursor.mjs), measured as
# seconds before the end of each WebM, since a tab's recording starts at its first paint.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
BASE="$REPO/docs/hn7-submission-pack/videos/out"
AUDIO="$BASE/audio"
SCREEN="$BASE/screen"
FINAL="$BASE/final"
mkdir -p "$FINAL"

dur() { ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$1"; }

mux() {
  local name="$1"
  local meta="$SCREEN/${name}.json"
  local mp3="$AUDIO/${name}.mp3"
  local mp4="$FINAL/hn7-${name}.mp4"
  for f in "$meta" "$mp3"; do
    [[ -f "$f" ]] || { echo "Missing $f (run generate_voiceover.py --timestamps and record_cursor.mjs)" >&2; return 1; }
  done

  local total fade_out
  total=$(python3 -c "print(round($(dur "$mp3") + 1.4, 2))")
  fade_out=$(python3 -c "print(round($total - 0.6, 2))")

  # One "file<TAB>start<TAB>end" line per segment, in raw-capture seconds.
  local -a inputs=()
  local filter="" labels="" n=0
  while IFS=$'\t' read -r file start end; do
    inputs+=(-i "$SCREEN/$file")
    local trim="start=${start}"
    [[ -n "$end" ]] && trim="${trim}:end=${end}"
    # Playwright records the 1280x720 page unscaled (older captures padded it into a grey
    # 1920x1080 frame), so crop to the page and upscale to 1080p.
    filter+="[${n}:v]trim=${trim},setpts=PTS-STARTPTS,crop=1280:720:0:0,scale=1920:1080:flags=lanczos,setsar=1,fps=30[s${n}];"
    labels+="[s${n}]"
    n=$((n + 1))
  done < <(SCREEN="$SCREEN" python3 - "$meta" <<'PY'
import json, os, subprocess, sys
meta = json.load(open(sys.argv[1]))
for seg in meta["segments"]:
    path = os.path.join(os.environ["SCREEN"], seg["file"])
    d = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path], text=True))
    start = max(0.0, d - seg["from_end"])
    end = d - seg["until_from_end"] if "until_from_end" in seg else ""
    print(seg["file"], f"{start:.3f}", f"{end:.3f}" if end != "" else "", sep="\t")
PY
)

  filter+="${labels}concat=n=${n}:v=1:a=0,tpad=stop_mode=clone:stop_duration=3,"
  filter+="fade=t=in:st=0:d=0.35,fade=t=out:st=${fade_out}:d=0.6,format=yuv420p[v];[${n}:a]apad[a]"
  ffmpeg -v error -y "${inputs[@]}" -i "$mp3" -filter_complex "$filter" \
    -map "[v]" -map "[a]" -t "$total" -r 30 \
    -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 192k -movflags +faststart "$mp4"

  local vd
  vd=$(ffprobe -v error -select_streams v -show_entries stream=duration -of default=nw=1:nk=1 "$mp4")
  echo "VERIFIED: $mp4 · total $(dur "$mp4")s · video stream ${vd}s"
}

tracks=("$@")
[[ ${#tracks[@]} -gt 0 ]] || tracks=(team demo technical)
for t in "${tracks[@]}"; do mux "$t"; done

echo "Upload files in $FINAL to HackOS."
