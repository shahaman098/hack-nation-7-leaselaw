"""Deterministic coverage + as-of evaluation over rule records.

Supports:
- Official RealPage schema (team_rule_id, status in_force/pending/...)
- Legacy fixture schema (rule_id, status enacted/pending)
"""

from __future__ import annotations

from datetime import date
from typing import Any


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    if len(s) == 4:
        return date(int(s), 1, 1)
    if len(s) == 7:
        y, m = s.split("-")
        return date(int(y), int(m), 1)
    return date.fromisoformat(s)


def rule_id(rule: dict[str, Any]) -> str:
    return rule.get("team_rule_id") or rule.get("rule_id") or ""


def rule_state(rule: dict[str, Any]) -> str | None:
    j = rule.get("jurisdiction")
    if isinstance(j, dict):
        return j.get("state")
    if isinstance(j, str):
        if ", " in j:
            return j.split(", ")[-1].strip()
        if len(j) == 2:
            return j.upper()
    return None


def rule_city(rule: dict[str, Any]) -> str | None:
    j = rule.get("jurisdiction")
    if isinstance(j, dict):
        return j.get("city")
    if isinstance(j, str) and ", " in j:
        return j.split(", ")[0].strip()
    level = rule.get("level")
    if level == "city" and isinstance(j, str) and len(j) > 2:
        return j
    return None


def normalize_status(rule: dict[str, Any], as_of: date) -> str:
    """Map schema status + effective_date into lookup result vocabulary."""
    status = rule.get("status") or "in_force"
    if status in ("pending", "failed"):
        return status
    eff = parse_date(rule.get("effective_date"))
    if eff and as_of < eff:
        return "not_yet_effective"
    if status in ("in_force", "enacted", "not_yet_effective"):
        # not_yet_effective in the rule file means as-of default; once past eff → applies
        return "applies"
    return status


def evaluate_rule(rule: dict[str, Any], addr: dict[str, Any], as_of: date) -> str:
    state = addr.get("state")
    # legal city if present, else mailing city
    city = addr.get("legal_city") or addr.get("city") or addr.get("postal_city")

    r_state = rule_state(rule)
    r_city = rule_city(rule)
    level = rule.get("level")
    if isinstance(rule.get("jurisdiction"), dict):
        level = rule["jurisdiction"].get("level") or level

    if r_state and r_state != state:
        return "out_of_jurisdiction"
    if level == "city" and r_city and r_city != city:
        # also allow postal_city match for Hoboken/Jersey City samples
        postal = addr.get("postal_city")
        if r_city != postal:
            return "out_of_jurisdiction"

    result = normalize_status(rule, as_of)
    if result in ("pending", "failed", "not_yet_effective"):
        return result

    cov = rule.get("coverage_conditions")
    if isinstance(cov, dict):
        max_coo = cov.get("max_certificate_of_occupancy")
        if max_coo and addr.get("year_built") is not None:
            cutoff = parse_date(max_coo)
            if cutoff and addr["year_built"] > cutoff.year:
                return "unknown"
            if cutoff and addr["year_built"] == cutoff.year:
                return "unknown"  # year_built ≠ certificate date
        if cov.get("min_units") is not None and addr.get("units") is None:
            return "unknown"

    return "applies"


def apply_supersession(rows: list[dict], rules: list[dict]) -> list[dict]:
    by_id = {rule_id(r): r for r in rules}
    for row in rows:
        rule = by_id.get(row["team_rule_id"]) or {}
        for other_id in rule.get("overrides") or rule.get("supersedes_state_rule_ids") or []:
            interaction = (rule.get("interaction") or "").lower()
            if "supersede" in interaction or "override" in interaction or rule.get(
                "supersedes_state_rule_ids"
            ):
                for x in rows:
                    if x["team_rule_id"] == other_id and x["result"] == "applies":
                        x["result"] = "superseded"
    # SF rent control vs CA statewide cap heuristic
    if any(r["team_rule_id"] == "SF-RENT-01" and r["result"] == "applies" for r in rows):
        for x in rows:
            if x["team_rule_id"] in {"CA-RENT-01", "CA-AB1482"} and x["result"] == "applies":
                x["result"] = "superseded"
    return rows


def lookup_address(
    addr: dict[str, Any], rules: list[dict[str, Any]], as_of_s: str
) -> dict[str, Any]:
    as_of = parse_date(as_of_s) or date(2026, 10, 1)
    rows: list[dict[str, Any]] = []
    for rule in rules:
        result = evaluate_rule(rule, addr, as_of)
        if result == "out_of_jurisdiction":
            continue
        if result == "failed":
            continue  # struck / failed — do not report as a rent cap
        rid = rule_id(rule)
        rows.append(
            {
                "team_rule_id": rid,
                "category": rule.get("category"),
                "result": result,
                "citation": rule.get("citation") or rule.get("source_citation"),
                "quoted_span": rule.get("quoted_span"),
                "plain_language": rule.get("requirement"),
                "explanation": rule.get("requirement"),
                "status": rule.get("status"),
                "effective_date": rule.get("effective_date"),
                "conflict_flag": bool(rule.get("conflict_flag")),
            }
        )
    rows = apply_supersession(rows, rules)
    return {
        "address_id": addr.get("address_id"),
        "street": addr.get("street") or addr.get("street_address"),
        "postal_city": addr.get("postal_city"),
        "state": addr.get("state"),
        "as_of": as_of_s,
        "jurisdiction_stack": addr.get("jurisdiction_stack")
        or [addr.get("state"), addr.get("postal_city")],
        "disclaimer": "Not legal advice. For Hack-Nation demo / research only.",
        "rules": rows,
    }
