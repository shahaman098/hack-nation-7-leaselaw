#!/usr/bin/env python3
"""Eval harness for RealPage change tests T1–T5 (+ optional gold fixtures)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data import load_addresses, load_change_tests, load_gold, load_rules  # noqa: E402
from src.engine import lookup_address  # noqa: E402
from src.export_outputs import build_changes  # noqa: E402


def _result(lookup: dict, rule_id: str) -> str | None:
    for r in lookup.get("rules") or []:
        if r.get("team_rule_id") == rule_id or r.get("rule_id") == rule_id:
            return r.get("result")
    return None


def eval_change_tests(addresses: list[dict], rules: list[dict]) -> list[dict]:
    by_state = lambda st: [a for a in addresses if a.get("state") == st]
    by_city = lambda city, st: [
        a
        for a in addresses
        if a.get("state") == st
        and (
            (a.get("legal_city") or "").lower() == city.lower()
            or (a.get("postal_city") or "").lower() == city.lower()
        )
    ]
    report: list[dict] = []

    # T1
    ca = by_state("CA")
    t1_ok = True
    bad = 0
    for a in ca:
        b = _result(lookup_address(a, rules, "2025-12-31"), "CA-ALG-01")
        aft = _result(lookup_address(a, rules, "2026-01-02"), "CA-ALG-01")
        if b != "not_yet_effective" or aft != "applies":
            t1_ok = False
            bad += 1
    report.append(
        {"test_id": "T1", "pass": t1_ok, "detail": f"{len(ca)-bad}/{len(ca)} CA addresses"}
    )

    # T2
    hob = by_city("Hoboken", "NJ")
    jc = by_city("Jersey City", "NJ")
    newark = by_city("Newark", "NJ")
    t2_ok = True
    for a in hob:
        if _result(lookup_address(a, rules, "2026-10-01"), "HOB-ALG-01") != "applies":
            t2_ok = False
        if _result(lookup_address(a, rules, "2026-10-01"), "JC-ALG-01") is not None:
            t2_ok = False
    for a in jc:
        if _result(lookup_address(a, rules, "2026-10-01"), "JC-ALG-01") != "applies":
            t2_ok = False
        if _result(lookup_address(a, rules, "2026-10-01"), "HOB-ALG-01") is not None:
            t2_ok = False
    for a in newark:
        lu = lookup_address(a, rules, "2026-10-01")
        if _result(lu, "HOB-ALG-01") is not None or _result(lu, "JC-ALG-01") is not None:
            t2_ok = False
    report.append(
        {
            "test_id": "T2",
            "pass": t2_ok,
            "detail": f"hob={len(hob)} jc={len(jc)} newark={len(newark)}",
        }
    )

    # T3
    nj = by_state("NJ")
    t3_ok = True
    for a in nj:
        b = _result(lookup_address(a, rules, "2026-10-01"), "NJ-ALG-01")
        aft = _result(lookup_address(a, rules, "2027-07-02"), "NJ-ALG-01")
        if b != "not_yet_effective" or aft != "applies":
            t3_ok = False
        # conflict flag on Hoboken/JC after effective
        if (a.get("legal_city") or a.get("postal_city")) in {"Hoboken", "Jersey City"}:
            aft_lu = lookup_address(a, rules, "2027-07-02")
            row = next(
                (r for r in aft_lu["rules"] if r.get("team_rule_id") == "NJ-ALG-01"),
                None,
            )
            if not row or not row.get("conflict_flag"):
                t3_ok = False
    report.append({"test_id": "T3", "pass": t3_ok, "detail": f"nj={len(nj)}"})

    # T4
    ma = by_state("MA")
    t4_ok = True
    for a in ma:
        lu = lookup_address(a, rules, "2026-10-01")
        if _result(lu, "MA-ALG-P1") != "pending" or _result(lu, "MA-ALG-P2") != "pending":
            t4_ok = False
    report.append({"test_id": "T4", "pass": t4_ok, "detail": f"ma={len(ma)}"})

    # T5 — no rent_increase_limits applies on MA addresses
    t5_ok = True
    rent_hits = 0
    for a in ma:
        lu = lookup_address(a, rules, "2026-10-01")
        for r in lu["rules"]:
            if r.get("category") == "rent_increase_limits" and r.get("result") == "applies":
                t5_ok = False
                rent_hits += 1
    # failed rule should exist in rules.json
    if not any(r.get("team_rule_id") == "MA-RENT-P1" and r.get("status") == "failed" for r in rules):
        t5_ok = False
    report.append(
        {"test_id": "T5", "pass": t5_ok, "detail": f"rent_cap_applies_hits={rent_hits}"}
    )

    # ensure change_tests file still present
    assert load_change_tests()
    build_changes(addresses, rules)  # smoke
    return report


def main() -> int:
    addresses = load_addresses()
    rules = load_rules()
    if not rules:
        print("No rules loaded", file=sys.stderr)
        return 1
    report = eval_change_tests(addresses, rules)

    # optional gold
    gold = load_gold()
    gold_report = []
    addr_map = {a["address_id"]: a for a in addresses}
    for case in gold.get("as_of_cases", []):
        if case["address_id"] not in addr_map:
            continue
        out = lookup_address(addr_map[case["address_id"]], rules, case["as_of"])
        hit = next(
            (
                r
                for r in out["rules"]
                if r.get("team_rule_id") == case.get("rule_id")
                or r.get("rule_id") == case.get("rule_id")
            ),
            None,
        )
        ok = bool(hit) and hit["result"] == case["expected_result"]
        gold_report.append({"case_id": case["case_id"], "pass": ok})

    passed = sum(1 for r in report if r["pass"])
    payload = {
        "passed": passed,
        "total": len(report),
        "change_tests": report,
        "gold": gold_report,
    }
    print(json.dumps(payload, indent=2))
    out_path = ROOT / "out" / "eval-report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    return 0 if passed == len(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
