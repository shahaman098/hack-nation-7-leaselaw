from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from .jurisdiction import attach_legal_city
from .paths import APP_ROOT, require_starter

DEFAULT_FIXTURES = APP_ROOT / "fixtures"


def fixtures_dir() -> Path:
    override = os.environ.get("LEASELAW_DATA")
    if override:
        return Path(override)
    return DEFAULT_FIXTURES


def load_sample_addresses() -> list[dict]:
    """Load ~500 official sample addresses from the RealPage starter pack."""
    path = require_starter() / "data" / "sample_addresses.csv"
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            year = row.get("year_built") or ""
            units = row.get("units") or ""
            rows.append(
                attach_legal_city(
                    {
                        "address_id": row["address_id"],
                        "street": row["street_address"],
                        "street_address": row["street_address"],
                        "postal_city": row["postal_city"],
                        "city": row["postal_city"],
                        "state": row["state"],
                        "zip": row["zip"],
                        "year_built": int(year) if year.strip().isdigit() else None,
                        "units": int(units) if units.strip().isdigit() else None,
                        "use_code": row.get("use_code"),
                        "use_description": row.get("use_description"),
                        "jurisdiction_stack": [row["state"], row["postal_city"]],
                    }
                )
            )
    return rows


def load_addresses() -> list[dict]:
    """Prefer starter sample; fall back to small fixtures."""
    try:
        return load_sample_addresses()
    except FileNotFoundError:
        return json.loads((fixtures_dir() / "addresses.json").read_text())


def load_rules() -> list[dict]:
    """Prefer extracted/out rules; then seed; then fixtures."""
    for candidate in (
        APP_ROOT / "out" / "rules.json",
        APP_ROOT / "fixtures" / "seed_rules.json",
        fixtures_dir() / "rules_fixture.json",
    ):
        if candidate.exists():
            data = json.loads(candidate.read_text())
            if isinstance(data, list) and data:
                return data
    return []


def load_change_tests() -> list[dict]:
    path = require_starter() / "dev" / "change_tests.json"
    return json.loads(path.read_text())


def load_gold() -> dict:
    path = fixtures_dir() / "gold_answers.json"
    if not path.exists():
        return {"as_of_cases": []}
    return json.loads(path.read_text())


def corpus_manifest() -> list[dict]:
    path = require_starter() / "corpus" / "corpus_manifest.csv"
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def starter_stats() -> dict:
    root = require_starter()
    texts = list((root / "corpus" / "text").glob("*.txt"))
    addrs = load_sample_addresses()
    return {
        "starter": str(root),
        "corpus_text_files": len(texts),
        "addresses": len(addrs),
        "has_schema": (root / "schema" / "rule_record.schema.json").exists(),
        "has_change_tests": (root / "dev" / "change_tests.json").exists(),
        "has_score_py": (root / "score.py").exists(),
        "note": "This pack is participant-no-scoring; score.py not included.",
    }
