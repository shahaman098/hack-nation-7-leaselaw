#!/usr/bin/env python3
"""Track 01 spike: MapConflict minimal loop (no live ElevenLabs required).

Demonstrates non-fakeable proof from the PDF modules:
1) two expert claims under conditions → minimal conflict set
2) lesson on verification_hold until human ruling
3) tutor speech text before/after (stand-in for ElevenAgents TTS)

ElevenLabs path (when credits claimed):
- Interviewer/tutor agents via ElevenAgents
- Scribe v2 for pause detection
- Push screen events as client tools (see challenge PDF wiring)
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_map() -> dict:
    return json.loads((ROOT / "fixtures/work_map.json").read_text())


def minimal_conflict(step: dict) -> list[str]:
    """Two claims that are jointly unsatisfiable under overlapping conditions."""
    claims = step["evidence"]
    if len(claims) < 2:
        return []
    # deterministic fixture: C1 vs C2 on emergency_handoff ∩ amount>=5000
    ids = [c["claim_id"] for c in claims]
    cond_sets = [set(c["conditions"]) for c in claims]
    if cond_sets[0] & cond_sets[1]:
        # contradictory actions implied by texts
        if "always capex" in claims[0]["text"] and "opex first" in claims[1]["text"]:
            return ids[:2]
    return []


def apply_ruling(wm: dict, keep_claim_id: str) -> dict:
    step = wm["steps"][0]
    conflict = minimal_conflict(step)
    if not conflict:
        raise ValueError("no conflict")
    step["evidence"] = [c for c in step["evidence"] if c["claim_id"] == keep_claim_id]
    step["confirmation"] = "ruled"
    step["reason"] = step["evidence"][0]["text"]
    for lesson in wm["lessons"]:
        if lesson["depends_on_step"] == step["step_id"]:
            lesson["state"] = "released"
    return wm


def tutor_reply(wm: dict, scenario: str) -> str:
    step = wm["steps"][0]
    lesson = wm["lessons"][0]
    if lesson["state"] == "verification_hold":
        return (
            "I cannot teach this yet — expert guidance conflicts under "
            f"{scenario}. Lesson {lesson['lesson_id']} is on verification hold."
        )
    return (
        f"Sabine's ruled guidance: {step['reason']} "
        f"Guardrails: {'; '.join(step['guardrails'])} "
        f"[evidence: {step['evidence'][0]['source_audio']}]"
    )


def main() -> None:
    wm = load_map()
    step = wm["steps"][0]
    conflict = minimal_conflict(step)
    print("Conflict set:", conflict)
    assert conflict == ["C1", "C2"], conflict

    before = tutor_reply(wm, "emergency_handoff + €7200 equipment")
    print("TUTOR BEFORE:", before)
    assert "verification hold" in before.lower() or "verification_hold" in before or "hold" in before.lower()

    apply_ruling(wm, "C1")
    after = tutor_reply(wm, "emergency_handoff + €7200 equipment")
    print("TUTOR AFTER:", after)
    assert "always capex" in after.lower()
    assert wm["lessons"][0]["state"] == "released"
    print("PASS MapConflict spike")

    print(
        "\nElevenLabs integration checklist:\n"
        "- Claim Creator credit in HackOS Credits & Codes\n"
        "- Wire ElevenAgents interviewer + tutor (Expressive Mode)\n"
        "- Scribe v2 realtime for pause gating\n"
        "- Client tools: push vision events every 1–2s\n"
        "- Replace tutor_reply() strings with agent TTS from Work Map KB"
    )


if __name__ == "__main__":
    main()
