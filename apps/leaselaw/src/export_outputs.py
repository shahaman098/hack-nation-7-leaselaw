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


def build_changes(addresses: list[dict], rules: list[dict]) -> dict:
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
    # attach per-test spot checks used by eval
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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # Prefer freshly extracted rules
    rules = extract_all()
    (OUT / "rules.json").write_text(json.dumps(rules, indent=2) + "\n")
    addresses = load_addresses()
    lookups = [lookup_address(a, rules, "2026-10-01") for a in addresses]
    (OUT / "lookups.json").write_text(json.dumps(lookups, indent=2) + "\n")
    changes = build_changes(addresses, rules)
    (OUT / "changes.json").write_text(json.dumps(changes, indent=2) + "\n")
    print(
        f"Wrote {OUT}/rules.json ({len(rules)} rules), "
        f"lookups.json ({len(lookups)}), changes.json T1–T5"
    )


if __name__ == "__main__":
    main()
