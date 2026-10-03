from __future__ import annotations

import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]

DEFAULT_STARTER = (
    REPO_ROOT
    / "briefs"
    / "hack-nation-7-realpage-starter"
    / "participant-final-no-hour16 3"
)


def starter_root() -> Path:
    override = os.environ.get("LEASELAW_STARTER")
    if override:
        return Path(override)
    return DEFAULT_STARTER


def require_starter() -> Path:
    root = starter_root()
    if not (root / "README.md").exists():
        raise FileNotFoundError(
            f"RealPage starter not found at {root}. "
            "Unpack the Drive zip into briefs/hack-nation-7-realpage-starter/"
        )
    return root
