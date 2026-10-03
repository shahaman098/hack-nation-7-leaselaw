from __future__ import annotations

from collections import Counter
from typing import Any

from hackforge.models import CompetitionBrief
from hackforge.paths import SCHEMAS_DIR
from hackforge.providers import DryRunProvider, LLMProvider
from hackforge.utils import load_prompt, read_json

from .models import TrackHint, VerifiedWinner, WinnerPatterns


def _deterministic_patterns(brief: CompetitionBrief, winners: list[VerifiedWinner]) -> WinnerPatterns:
    mech_counter: Counter[str] = Counter()
    demo_counter: Counter[str] = Counter()
    track_hint_map: dict[str, list[str]] = {}
    for winner in winners:
        mech_counter[winner.mechanism] += 1
        demo_counter[winner.demo_hook] += 1
        if winner.track:
            track_hint_map.setdefault(winner.track, []).append(winner.mechanism)
    top_mechs = [m for m, _ in mech_counter.most_common(8)]
    top_demos = [d for d, _ in demo_counter.most_common(6)]
    archetypes = [
        f"{w.primary_user}: {w.problem[:80]}" for w in winners[: min(6, len(winners))]
    ]
    anti = list(brief.crowding.do_not_build[:6]) if brief.crowding else []
    return WinnerPatterns(
        competition=brief.name,
        winning_archetypes=archetypes,
        mechanism_families=top_mechs,
        demo_patterns=top_demos,
        anti_patterns=anti,
        track_hints=[
            TrackHint(track=track, mechanisms=mechanisms[:4])
            for track, mechanisms in track_hint_map.items()
        ],
        source_winner_ids=[w.id for w in winners],
    )


def build_winner_patterns(
    provider: LLMProvider,
    brief: CompetitionBrief,
    winners: list[VerifiedWinner],
) -> WinnerPatterns:
    if not winners or isinstance(provider, DryRunProvider):
        return _deterministic_patterns(brief, winners)

    template, _ = load_prompt("winner-patterns")
    schema = read_json(SCHEMAS_DIR / "winner-patterns.json")
    catalog = [
        {
            "id": w.id,
            "primary_user": w.primary_user,
            "problem": w.problem,
            "mechanism": w.mechanism,
            "demo_hook": w.demo_hook,
            "track": w.track,
            "event_date": w.event_date,
        }
        for w in winners
    ]
    payload: dict[str, Any] = {
        "competition": brief.model_dump(),
        "verified_winners": catalog,
    }
    data = provider.complete_json(template, str(payload), schema=schema)
    if not isinstance(data, dict):
        raise ValueError("Winner pattern extraction did not return an object")
    data.setdefault("competition", brief.name)
    data.setdefault("source_winner_ids", [w.id for w in winners])
    return WinnerPatterns.model_validate(data)
