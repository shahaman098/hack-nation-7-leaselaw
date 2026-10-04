#!/usr/bin/env python3
"""Export rules.json / lookups.json / changes.json (T1–T5) for all addresses."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data import load_addresses, load_change_tests, load_rules  # noqa: E402
from src.engine import lookup_address  # noqa: E402
from src.extract_rules import extract_all  # noqa: E402

OUT = ROOT / "out"
DEBUG = OUT / "debug"
DEFAULT_AS_OF = "2026-10-01"


def _by_state(addresses: list[dict], state: str) -> list[dict]:
    return [a for a in addresses if a.get("state") == state]


def _by_city(addresses: list[dict], city: str, state: str) -> list[dict]:
    city_l = city.lower()
    return [
        a
        for a in addresses
        if a.get("state") == state
        and (
            (a.get("legal_city") or "").lower() == city_l
            or (a.get("postal_city") or "").lower() == city_l
        )
    ]


def _rule_result(lookup: dict, rule_id: str) -> str | None:
    for r in lookup.get("rules") or []:
        if r.get("team_rule_id") == rule_id or r.get("rule_id") == rule_id:
            return r.get("result")
    return None


def _submission_row(rule_row: dict) -> dict:
    return {
        "team_rule_id": rule_row["team_rule_id"],
        "result": rule_row["result"],
        "explanation": rule_row.get("explanation") or rule_row.get("plain_language") or "",
        "conflict_flag": bool(rule_row.get("conflict_flag")),
    }


def build_lookups_submission(addresses: list[dict], rules: list[dict], as_of: str) -> dict:
    lookups: dict[str, list[dict]] = {}
    for a in addresses:
        full = lookup_address(a, rules, as_of)
        lookups[a["address_id"]] = [_submission_row(r) for r in full.get("rules") or []]
    return {"as_of": as_of, "lookups": lookups}


def build_changes_submission(addresses: list[dict], rules: list[dict]) -> dict:
    tests = {t["test_id"]: t for t in load_change_tests()}
    ca = _by_state(addresses, "CA")
    nj = _by_state(addresses, "NJ")
    ma = _by_state(addresses, "MA")
    hob = _by_city(addresses, "Hoboken", "NJ")
    jc = _by_city(addresses, "Jersey City", "NJ")

    t1 = tests["T1"]
    t3 = tests["T3"]
    t4 = tests["T4"]
    t5 = tests["T5"]

    t2_affected = [a["address_id"] for a in hob + jc]
    t3_conflicts = [a["address_id"] for a in hob + jc]

    return {
        "T1": {
            "affected_address_ids": [a["address_id"] for a in ca],
            "conflict_flag_address_ids": [],
            "notes": t1["expected_behavior"],
        },
        "T2": {
            "affected_address_ids": t2_affected,
            "conflict_flag_address_ids": [],
            "notes": tests["T2"]["expected_behavior"],
        },
        "T3": {
            "affected_address_ids": [a["address_id"] for a in nj],
            "conflict_flag_address_ids": t3_conflicts,
            "notes": t3["expected_behavior"],
        },
        "T4": {
            "affected_address_ids": [a["address_id"] for a in ma],
            "conflict_flag_address_ids": [],
            "notes": t4["expected_behavior"],
        },
        "T5": {
            "affected_address_ids": [],
            "conflict_flag_address_ids": [],
            "notes": t5["expected_behavior"],
        },
    }


def build_changes_detail(addresses: list[dict], rules: list[dict]) -> dict:
    """Rich before/after payloads for demo + eval smoke."""
    tests = {t["test_id"]: t for t in load_change_tests()}
    ca = _by_state(addresses, "CA")
    nj = _by_state(addresses, "NJ")
    ma = _by_state(addresses, "MA")
    hob = _by_city(addresses, "Hoboken", "NJ")
    jc = _by_city(addresses, "Jersey City", "NJ")
    newark = _by_city(addresses, "Newark", "NJ")

    sample_ca = ca[0] if ca else addresses[0]
    sample_ma = ma[0] if ma else addresses[0]
    sample_hob = hob[0] if hob else None
    sample_jc = jc[0] if jc else None
    sample_newark = newark[0] if newark else None

    t1 = tests["T1"]
    t3 = tests["T3"]

    changes: dict = {
        "T1": {
            "title": t1["title"],
            "description": t1["expected_behavior"],
            "rule_ids": t1["rule_ids"],
            "sample_address_id": sample_ca["address_id"],
            "before": lookup_address(sample_ca, rules, t1["as_of_before"]),
            "after": lookup_address(sample_ca, rules, t1["as_of_after"]),
            "affected_count": len(ca),
        },
        "T2": {
            "title": tests["T2"]["title"],
            "description": tests["T2"]["expected_behavior"],
            "rule_ids": tests["T2"]["rule_ids"],
            "as_of": tests["T2"]["as_of"],
            "hoboken": lookup_address(sample_hob, rules, tests["T2"]["as_of"])
            if sample_hob
            else None,
            "jersey_city": lookup_address(sample_jc, rules, tests["T2"]["as_of"])
            if sample_jc
            else None,
            "newark": lookup_address(sample_newark, rules, tests["T2"]["as_of"])
            if sample_newark
            else None,
        },
        "T3": {
            "title": t3["title"],
            "description": t3["expected_behavior"],
            "rule_ids": t3["rule_ids"],
            "sample_address_id": (jc[0] if jc else nj[0])["address_id"] if nj else None,
            "before": lookup_address(jc[0] if jc else nj[0], rules, t3["as_of_before"])
            if nj
            else None,
            "after": lookup_address(jc[0] if jc else nj[0], rules, t3["as_of_after"])
            if nj
            else None,
            "conflict_with": t3.get("conflict_with"),
            "affected_count": len(nj),
        },
        "T4": {
            "title": tests["T4"]["title"],
            "description": tests["T4"]["expected_behavior"],
            "rule_ids": tests["T4"]["rule_ids"],
            "as_of": tests["T4"]["as_of"],
            "sample_address_id": sample_ma["address_id"],
            "as_of_lookup": lookup_address(sample_ma, rules, tests["T4"]["as_of"]),
            "affected_count": len(ma),
        },
        "T5": {
            "title": tests["T5"]["title"],
            "description": tests["T5"]["expected_behavior"],
            "rule_ids": tests["T5"]["rule_ids"],
            "as_of": tests["T5"]["as_of"],
            "sample_address_id": sample_ma["address_id"],
            "as_of_lookup": lookup_address(sample_ma, rules, tests["T5"]["as_of"]),
            "rent_cap_applies_count": sum(
                1
                for a in ma
                if any(
                    r.get("category") == "rent_increase_limits"
                    and r.get("result") == "applies"
                    for r in lookup_address(a, rules, tests["T5"]["as_of"])["rules"]
                )
            ),
        },
    }
    changes["_spot"] = {
        "T1_before": _rule_result(changes["T1"]["before"], "CA-ALG-01"),
        "T1_after": _rule_result(changes["T1"]["after"], "CA-ALG-01"),
        "T2_hob": _rule_result(changes["T2"]["hoboken"] or {}, "HOB-ALG-01"),
        "T2_jc": _rule_result(changes["T2"]["jersey_city"] or {}, "JC-ALG-01"),
        "T2_newark_hob": _rule_result(changes["T2"]["newark"] or {}, "HOB-ALG-01"),
        "T2_newark_jc": _rule_result(changes["T2"]["newark"] or {}, "JC-ALG-01"),
        "T3_before": _rule_result(changes["T3"]["before"] or {}, "NJ-ALG-01"),
        "T3_after": _rule_result(changes["T3"]["after"] or {}, "NJ-ALG-01"),
        "T4_p1": _rule_result(changes["T4"]["as_of_lookup"], "MA-ALG-P1"),
        "T4_p2": _rule_result(changes["T4"]["as_of_lookup"], "MA-ALG-P2"),
        "T5_rent_caps": changes["T5"]["rent_cap_applies_count"],
    }
    return changes


def build_changes(addresses: list[dict], rules: list[dict]) -> dict:
    """Backward-compatible: submission-shaped changes (eval smoke)."""
    return build_changes_submission(addresses, rules)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DEBUG.mkdir(parents=True, exist_ok=True)
    rules = extract_all()
    (OUT / "rules.json").write_text(json.dumps(rules, indent=2) + "\n")
    addresses = load_addresses()
    detail = [lookup_address(a, rules, DEFAULT_AS_OF) for a in addresses]
    (DEBUG / "lookups_detail.json").write_text(json.dumps(detail, indent=2) + "\n")
    submission = build_lookups_submission(addresses, rules, DEFAULT_AS_OF)
    (OUT / "lookups.json").write_text(json.dumps(submission, indent=2) + "\n")
    (DEBUG / "changes_detail.json").write_text(
        json.dumps(build_changes_detail(addresses, rules), indent=2) + "\n"
    )
    (OUT / "changes.json").write_text(
        json.dumps(build_changes_submission(addresses, rules), indent=2) + "\n"
    )
    print(
        f"Wrote {OUT}/rules.json ({len(rules)} rules), "
        f"lookups.json ({len(submission['lookups'])}), changes.json T1–T5"
    )


if __name__ == "__main__":
    main()
