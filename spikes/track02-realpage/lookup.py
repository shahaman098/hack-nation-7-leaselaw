#!/usr/bin/env python3
"""Track 02 spike: address-level rule lookup with as-of-date toggle.

Uses local fixtures (not the full RealPage corpus). Demonstrates:
- jurisdiction stack
- applies / not_yet_effective / pending / superseded
- citations + quoted spans
- law-change toggle (AB325 before/after 2026-01-01)
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def load() -> tuple[list[dict], list[dict], dict]:
    addresses = json.loads((ROOT / "fixtures/addresses.json").read_text())
    rules = json.loads((ROOT / "fixtures/rules_fixture.json").read_text())
    gold = json.loads((ROOT / "gold_answers.json").read_text())
    return addresses, rules, gold


def result_for_rule(rule: dict, addr: dict, as_of: date) -> str:
    state = addr["state"]
    city = addr["city"]
    j = rule["jurisdiction"]
    if j.get("state") and j["state"] != state:
        return "out_of_jurisdiction"
    if j.get("level") == "city" and j.get("city") and j["city"] != city:
        return "out_of_jurisdiction"

    status = rule.get("status", "enacted")
    eff = parse_date(rule["effective_date"])
    if status == "pending":
        return "pending"
    if as_of < eff:
        return "not_yet_effective"

    if rule.get("effect") == "no_local_rent_cap":
        return "applies_meta"  # meta rule explaining absence of local cap

    cov = rule.get("coverage_conditions") or {}
    max_coo = cov.get("max_certificate_of_occupancy")
    if max_coo and addr.get("year_built"):
        # approximate: year_built as proxy for certificate year
        if addr["year_built"] > parse_date(max_coo).year:
            return "unknown"

    return "applies"


def lookup(address_id: str, as_of_s: str, *, addresses: list, rules: list) -> dict:
    as_of = parse_date(as_of_s)
    addr = next(a for a in addresses if a["address_id"] == address_id)
    rows = []
    for rule in rules:
        r = result_for_rule(rule, addr, as_of)
        if r == "out_of_jurisdiction":
            continue
        # supersession: if local rent rule applies, mark state rent cap superseded
        if (
            rule["rule_id"] == "CA-AB1482"
            and any(
                result_for_rule(x, addr, as_of) == "applies" and x["rule_id"] == "SF-CH37"
                for x in rules
            )
        ):
            r = "superseded"
        rows.append(
            {
                "rule_id": rule["rule_id"],
                "category": rule["category"],
                "result": r,
                "citation": rule["source_citation"],
                "quoted_span": rule["quoted_span"],
                "plain_language": rule["requirement"],
                "status": rule.get("status"),
                "effective_date": rule["effective_date"],
            }
        )
    return {
        "address_id": address_id,
        "as_of": as_of_s,
        "jurisdiction_stack": addr["jurisdiction_stack"],
        "disclaimer": "Not legal advice. Spike fixture only.",
        "rules": rows,
    }


def check_gold(addresses: list, rules: list, gold: dict) -> list[dict]:
    report = []
    for case in gold["as_of_cases"]:
        out = lookup(case["address_id"], case["as_of"], addresses=addresses, rules=rules)
        if case.get("case_id") == "BOS-no-rent-cap":
            ok = any(r["rule_id"] == "MA-40P" for r in out["rules"]) and not any(
                r["category"] == "rent_increase_limits"
                and r["result"] == "applies"
                and r["rule_id"] != "MA-40P"
                for r in out["rules"]
            )
            report.append(
                {
                    "case_id": case["case_id"],
                    "expected": "no_local_rent_cap",
                    "actual": "ok" if ok else "invented_or_missing",
                    "pass": ok,
                }
            )
            continue
        hit = next((r for r in out["rules"] if r["rule_id"] == case["rule_id"]), None)
        actual = hit["result"] if hit else "missing"
        expected = case["expected_result"]
        report.append(
            {
                "case_id": case["case_id"],
                "expected": expected,
                "actual": actual,
                "pass": actual == expected,
            }
        )
    return report


def main() -> None:
    addresses, rules, gold = load()
    print("=== Killer demo: SF address, AB325 before vs after ===")
    before = lookup("SF-20U-1962", "2025-12-31", addresses=addresses, rules=rules)
    after = lookup("SF-20U-1962", "2026-01-02", addresses=addresses, rules=rules)
    for label, packet in [("BEFORE", before), ("AFTER", after)]:
        ab = next(r for r in packet["rules"] if r["rule_id"] == "CA-AB325")
        print(f"{label} {packet['as_of']}: CA-AB325 => {ab['result']} · {ab['citation']}")

    print("\n=== Gold check ===")
    report = check_gold(addresses, rules, gold)
    for row in report:
        print(row)
    failed = [r for r in report if not r.get("pass")]
    print(f"\nPASS {len(report) - len(failed)}/{len(report)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
