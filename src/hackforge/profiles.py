from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from hackforge.paths import FIXTURES_DIR, REPO_ROOT


@dataclass(frozen=True)
class CompetitionProfile:
    id: str
    display_name: str
    description: str = ""
    tracks_fixture: Path | None = None
    winner_corpus: Path | None = None
    training_cutoff: str | None = None
    inspiration_min: float | None = None
    search_profile: str | None = None
    finalists: int | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> CompetitionProfile:
        tracks = data.get("tracks_fixture")
        corpus = data.get("winner_corpus")
        return cls(
            id=str(data.get("id") or ""),
            display_name=str(data.get("display_name") or data.get("id") or ""),
            description=str(data.get("description") or "").strip(),
            tracks_fixture=Path(tracks) if tracks else None,
            winner_corpus=Path(corpus) if corpus else None,
            training_cutoff=data.get("training_cutoff"),
            inspiration_min=float(data["inspiration_min"]) if data.get("inspiration_min") is not None else None,
            search_profile=data.get("search_profile"),
            finalists=int(data["finalists"]) if data.get("finalists") is not None else None,
        )


def load_competition_profile(name: str) -> CompetitionProfile:
    path = REPO_ROOT / "profiles" / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Competition profile not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Profile {name} is not a mapping")
    profile = CompetitionProfile.from_mapping(data)
    if profile.id != name:
        raise ValueError(f"Profile id {profile.id!r} does not match requested name {name!r}")
    return profile


def resolve_tracks_fixture(profile: CompetitionProfile) -> Path | None:
    if not profile.tracks_fixture:
        return None
    candidate = REPO_ROOT / profile.tracks_fixture
    if candidate.exists():
        return candidate
    alt = FIXTURES_DIR / profile.tracks_fixture.name
    return alt if alt.exists() else candidate


def apply_profile_defaults(
    profile: CompetitionProfile,
    *,
    search_profile: str,
    finalists: int,
    training_cutoff: str | None,
    inspiration_min: float | None,
) -> tuple[str, int, str | None, float | None]:
    return (
        profile.search_profile or search_profile,
        profile.finalists or finalists,
        training_cutoff or profile.training_cutoff,
        inspiration_min if inspiration_min is not None else profile.inspiration_min,
    )
