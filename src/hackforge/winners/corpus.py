from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import jsonschema

from hackforge.paths import CORPORA_DIR, REPO_ROOT, SCHEMAS_DIR
from hackforge.utils import read_json

from .models import VerifiedWinner

_WINNER_SCHEMA = read_json(SCHEMAS_DIR / "winner.json")


def _default_corpus_path() -> Path:
    return CORPORA_DIR / "verified-winners" / "seed.jsonl"


def load_verified_winners(corpus_path: Path | str | None = None) -> list[VerifiedWinner]:
    path = Path(corpus_path) if corpus_path else _default_corpus_path()
    if not path.is_absolute():
        candidate = REPO_ROOT / path
        path = candidate if candidate.exists() else _default_corpus_path()
    if not path.exists():
        return []
    winners: list[VerifiedWinner] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            jsonschema.validate(row, _WINNER_SCHEMA)
            winners.append(VerifiedWinner.model_validate(row))
    return winners


def filter_training_cutoff(
    winners: list[VerifiedWinner],
    *,
    cutoff: str | None = None,
) -> list[VerifiedWinner]:
    raw = cutoff or os.getenv("HACKFORGE_TRAINING_CUTOFF")
    if not raw:
        return winners
    try:
        limit = date.fromisoformat(raw.strip())
    except ValueError:
        return winners
    kept: list[VerifiedWinner] = []
    for winner in winners:
        try:
            event = date.fromisoformat(winner.event_date)
        except ValueError:
            kept.append(winner)
            continue
        if event <= limit:
            kept.append(winner)
    return kept
