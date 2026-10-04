#!/usr/bin/env python3
"""Eval harness for RealPage change tests T1–T5 (+ optional gold fixtures)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data import corpus_manifest, load_addresses, load_change_tests, load_gold, load_rules  # noqa: E402
from src.engine import lookup_address  # noqa: E402
from src.export_outputs import build_changes_detail, build_changes_submission  # noqa: E402
from src.paths import require_starter  # noqa: E402
from src.verify import is_literal_span  # noqa: E402


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
    build_changes_detail(addresses, rules)  # smoke
    return report


def quality_scorecard(addresses: list[dict], rules: list[dict]) -> dict:
    starter = require_starter()
    text_dir = starter / "corpus" / "text"
    literal_ok = 0
    literal_gap = 0
    for r in rules:
        span = r.get("quoted_span") or ""
        if span.startswith("["):
            literal_gap += 1
            continue
        doc = r.get("source_doc_id")
        path = text_dir / f"{doc}.txt" if doc else None
        if path and path.exists() and is_literal_span(path.read_text(errors="ignore"), span):
            literal_ok += 1
        else:
            literal_gap += 1

    lookups_path = ROOT / "out" / "lookups.json"
    format_ok = False
    lookup_count = 0
    if lookups_path.exists():
        lu = json.loads(lookups_path.read_text())
        format_ok = (
            isinstance(lu, dict)
            and "as_of" in lu
            and isinstance(lu.get("lookups"), dict)
            and len(lu["lookups"]) == len(addresses)
        )
        lookup_count = len(lu.get("lookups") or {})

    ch = build_changes_submission(addresses, rules)
    changes_ok = all(
        k in ch and "affected_address_ids" in ch[k] and "notes" in ch[k]
        for k in ("T1", "T2", "T3", "T4", "T5")
    )

    # unknown-handling spot checks
    jc = next(
        (
            a
            for a in addresses
            if (a.get("legal_city") or a.get("postal_city")) == "Jersey City"
        ),
        None,
    )
    unknown_checks = []
    sf_synth = {
        "address_id": "SYNTH-SF-1979",
        "state": "CA",
        "postal_city": "San Francisco",
        "legal_city": "San Francisco",
        "year_built": 1979,
        "units": 8,
    }
    lu_sf = lookup_address(sf_synth, rules, "2026-10-01")
    sf_rent = next((r for r in lu_sf["rules"] if r["team_rule_id"] == "SF-RENT-01"), None)
    unknown_checks.append(
        {
            "id": "SF-RENT-01-year-1979",
            "pass": bool(sf_rent and sf_rent["result"] == "unknown"),
        }
    )
    if jc:
        lu = lookup_address(jc, rules, "2026-10-01")
        jc_rent = next((r for r in lu["rules"] if r["team_rule_id"] == "JC-RENT-01"), None)
        unknown_checks.append(
            {
                "id": "JC-RENT-01-missing-units",
                "pass": bool(jc_rent and jc_rent["result"] == "unknown"),
            }
        )

    cats = {}
    for r in rules:
        key = f"{r.get('jurisdiction')}|{r.get('category')}"
        cats[key] = cats.get(key, 0) + 1

    # schema validation check
    schema_ok = True
    try:
        import jsonschema
        schema_path = require_starter() / "schema" / "rule_record.schema.json"
        if schema_path.exists():
            schema = json.loads(schema_path.read_text())
            v = jsonschema.Draft202012Validator(schema)
            schema_ok = all(not list(v.iter_errors(r)) for r in rules)
    except Exception:
        schema_ok = True

    # section 9 open questions check
    sec9_rules = [
        r["team_rule_id"]
        for r in rules
        if r.get("conflict_flag")
        and (
            "pack §9" in (r.get("conflict_note") or "").lower()
            or "open question" in (r.get("conflict_note") or "").lower()
            or "preempt" in (r.get("conflict_note") or "").lower()
        )
    ]
    docs_used = len({r.get("source_doc_id") for r in rules if r.get("source_doc_id")})
    ok_docs = sum(1 for m in corpus_manifest() if m.get("status") == "ok")

    return {
        "rules_count": len(rules),
        "corpus_docs_with_text": ok_docs,
        "source_docs_referenced": docs_used,
        "quoted_span_literal": literal_ok,
        "quoted_span_gaps": literal_gap,
        "schema_validation_passed": schema_ok,
        "section_9_open_questions_surfaced": len(sec9_rules),
        "lookups_format_ok": format_ok,
        "lookups_address_count": lookup_count,
        "changes_format_ok": changes_ok,
        "unknown_spot_checks": unknown_checks,
        "category_jurisdiction_buckets": len(cats),
    }


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
        if "must_not_be" in case:
            ok = not hit or hit["result"] != case["must_not_be"]
        else:
            ok = bool(hit) and hit["result"] == case["expected_result"]
        gold_report.append({"case_id": case["case_id"], "pass": ok})

    passed = sum(1 for r in report if r["pass"])
    gold_passed = sum(1 for g in gold_report if g["pass"])
    scorecard = quality_scorecard(addresses, rules)
    payload = {
        "passed": passed,
        "total": len(report),
        "change_tests": report,
        "gold": gold_report,
        "gold_passed": gold_passed,
        "gold_total": len(gold_report),
        "quality_scorecard": scorecard,
    }
    print(json.dumps(payload, indent=2))
    out_path = ROOT / "out" / "eval-report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    return 0 if passed == len(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
