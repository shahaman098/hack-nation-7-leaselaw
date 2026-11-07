#!/usr/bin/env python3
"""ElevenLabs TTS from narrations/*.txt or beats/*.json (segment-synced videos)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NARR = ROOT / "docs" / "hn7-submission-pack" / "videos" / "narrations"
BEATS = ROOT / "docs" / "hn7-submission-pack" / "videos" / "beats"
OUT = ROOT / "docs" / "hn7-submission-pack" / "videos" / "out" / "audio"

TRACKS = ("team", "demo", "technical")


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def concat_mp3(parts: list[Path], dest: Path) -> None:
    if len(parts) == 1:
        dest.write_bytes(parts[0].read_bytes())
        return
    list_file = dest.with_suffix(".concat.txt")
    list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in parts) + "\n", encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(dest)],
        check=True,
        capture_output=True,
    )
    list_file.unlink(missing_ok=True)


def synthesize(text: str, api_key: str, voice_id: str, model_id: str) -> bytes:
    import requests

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text.strip(),
        "model_id": model_id,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.85, "style": 0.2},
    }
    r = requests.post(url, json=payload, headers=headers, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs HTTP {r.status_code}: {r.text[:500]}")
    return r.content


def synthesize_with_timestamps(text: str, api_key: str, voice_id: str, model_id: str) -> tuple[bytes, dict]:
    """Same voice, plus per-character timing so cursor actions can be cued to words."""
    import base64

    import requests

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "text": text.strip(),
        "model_id": model_id,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.85, "style": 0.2},
    }
    r = requests.post(url, json=payload, headers=headers, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs HTTP {r.status_code}: {r.text[:500]}")
    data = r.json()
    return base64.b64decode(data["audio_base64"]), data.get("alignment") or {}


def synth_track_legacy(name: str, api_key: str, voice_id: str, model_id: str, timestamps: bool = False) -> None:
    src = NARR / f"{name}.txt"
    text = src.read_text(encoding="utf-8")
    print(f"Synthesizing {name} ({len(text)} chars)...")
    if timestamps:
        audio, alignment = synthesize_with_timestamps(text, api_key, voice_id, model_id)
        align_path = OUT / f"{name}.alignment.json"
        align_path.write_text(json.dumps(alignment), encoding="utf-8")
        print(f"Wrote {align_path}")
    else:
        audio = synthesize(text, api_key, voice_id, model_id)
    dest = OUT / f"{name}.mp3"
    dest.write_bytes(audio)
    print(f"Wrote {dest} ({len(audio)} bytes, {ffprobe_duration(dest):.1f}s)")


def synth_track_beats(name: str, api_key: str, voice_id: str, model_id: str) -> None:
    beats_path = BEATS / f"{name}.json"
    data = json.loads(beats_path.read_text(encoding="utf-8"))
    seg_dir = OUT / name
    seg_dir.mkdir(parents=True, exist_ok=True)
    manifest_segments: list[dict] = []
    mp3_parts: list[Path] = []

    for seg in data["segments"]:
        sid = seg["id"]
        text = seg["narration"]
        print(f"  {name}/{sid} ({len(text)} chars)...")
        audio = synthesize(text, api_key, voice_id, model_id)
        mp3 = seg_dir / f"{sid}.mp3"
        mp3.write_bytes(audio)
        dur = ffprobe_duration(mp3)
        mp3_parts.append(mp3)
        manifest_segments.append(
            {
                "id": sid,
                "duration_sec": round(dur, 3),
                "action": seg["action"],
                "mp3": mp3.name,
            }
        )
        print(f"    -> {mp3.name} {dur:.1f}s")

    manifest = {"track": name, "segments": manifest_segments}
    (seg_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    full = OUT / f"{name}.mp3"
    concat_mp3(mp3_parts, full)
    total = ffprobe_duration(full)
    print(f"Wrote {seg_dir}/manifest.json + {full} ({total:.1f}s total)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--track", choices=TRACKS)
    parser.add_argument(
        "--beats",
        action="store_true",
        help="Use videos/beats/{track}.json segments (record_beats.mjs pipeline)",
    )
    parser.add_argument(
        "--timestamps",
        action="store_true",
        help="Write <track>.alignment.json character timings (record_cursor.mjs pipeline)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("XI_API_KEY")
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
    model_id = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

    if not api_key or not voice_id:
        print(
            "Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID (clone your voice first).",
            file=sys.stderr,
        )
        return 1

    tracks = list(TRACKS) if args.all else ([args.track] if args.track else [])
    if not tracks:
        parser.error("use --all or --track team|demo|technical")

    OUT.mkdir(parents=True, exist_ok=True)
    for name in tracks:
        if args.beats:
            synth_track_beats(name, api_key, voice_id, model_id)
        else:
            synth_track_legacy(name, api_key, voice_id, model_id, timestamps=args.timestamps)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
