#!/usr/bin/env python3
"""Generate ElevenLabs TTS from narrations/*.txt using ELEVENLABS_VOICE_ID."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NARR = ROOT / "docs" / "hn7-submission-pack" / "videos" / "narrations"
OUT = ROOT / "docs" / "hn7-submission-pack" / "videos" / "out" / "audio"

TRACKS = ("team", "demo", "technical")


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--track", choices=TRACKS)
    args = parser.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("XI_API_KEY")
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
    model_id = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

    if not api_key or not voice_id:
        print(
            "Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID (clone your voice first).",
            file=sys.stderr,
        )
        print("See docs/hn7-submission-pack/videos/README.md", file=sys.stderr)
        return 1

    tracks = list(TRACKS) if args.all else ([args.track] if args.track else [])
    if not tracks:
        parser.error("use --all or --track team|demo|technical")

    OUT.mkdir(parents=True, exist_ok=True)
    for name in tracks:
        src = NARR / f"{name}.txt"
        text = src.read_text(encoding="utf-8")
        print(f"Synthesizing {name} ({len(text)} chars)...")
        audio = synthesize(text, api_key, voice_id, model_id)
        dest = OUT / f"{name}.mp3"
        dest.write_bytes(audio)
        print(f"Wrote {dest} ({len(audio)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
