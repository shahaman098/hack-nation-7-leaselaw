"""Structured coverage metadata keyed by team_rule_id (Module B)."""

from __future__ import annotations

import json
from pathlib import Path

from .paths import APP_ROOT

# Vocabulary consumed by engine.evaluate_rule coverage logic.
DEFAULT_COVERAGE: dict[str, dict] = {
    "CA-RENT-01": {
        "rolling_age_years": 15,
        "min_units": 2,
        "note": "AB 1482 statewide cap; local rent control may supersede.",
    },
    "SF-RENT-01": {
        "certificate_of_occupancy_before": "1979-06-13",
        "note": "Certificate date may differ from year_built in assessor data.",
    },
    "SF-RENT-02": {
        "certificate_of_occupancy_before": "1979-06-13",
    },
    "LA-RSO-01": {
        "certificate_of_occupancy_before": "1978-10-01",
    },
    "LA-RSO-02": {
        "certificate_of_occupancy_before": "1978-10-01",
    },
    "JC-RENT-01": {"min_units": 1, "note": "Unit count missing for most JC sample rows."},
    "NJ-DEP-01": {"owner_type_exemption": True},
    "NJ-DEP-02": {"owner_type_exemption": True},
}


def load_coverage() -> dict[str, dict]:
    path = APP_ROOT / "out" / "rule_coverage.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            merged = dict(DEFAULT_COVERAGE)
            merged.update(data)
            return merged
    return dict(DEFAULT_COVERAGE)


def save_coverage(data: dict[str, dict]) -> None:
    path = APP_ROOT / "out" / "rule_coverage.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
