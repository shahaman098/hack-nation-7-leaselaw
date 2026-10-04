"""Deterministic coverage + as-of evaluation over rule records."""

from __future__ import annotations

from datetime import date
from typing import Any

from .rule_coverage import load_coverage

_MANIFEST_RETRIEVAL: dict[str, str] = {}


def _manifest_retrieval(source_doc_id: str | None) -> str | None:
    if not source_doc_id:
        return None
    if not _MANIFEST_RETRIEVAL:
        try:
            from .data import corpus_manifest

            for row in corpus_manifest():
                _MANIFEST_RETRIEVAL[row["doc_id"]] = row.get("retrieved_at") or ""
        except OSError:
            pass
    return _MANIFEST_RETRIEVAL.get(source_doc_id) or None


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


def _coverage_dict(rule: dict[str, Any]) -> dict:
    cov = rule.get("coverage_conditions")
    if isinstance(cov, dict):
        base = dict(cov)
    else:
        base = {}
    extra = load_coverage().get(rule_id(rule), {})
    base.update(extra)
    return base


def normalize_status(rule: dict[str, Any], as_of: date) -> str:
    status = rule.get("status") or "in_force"
    if status in ("pending", "failed"):
        return status
    eff = parse_date(rule.get("effective_date"))
    if eff and as_of < eff:
        return "not_yet_effective"
    if status in ("in_force", "enacted", "not_yet_effective"):
        return "applies"
    return status


def _explain(
    rule: dict[str, Any],
    addr: dict[str, Any],
    as_of: date,
    result: str,
    reason: str,
) -> str:
    doc = rule.get("source_doc_id") or "?"
    retr = rule.get("source_retrieved_at") or _manifest_retrieval(doc) or "unknown"
    facts = []
    if addr.get("year_built") is not None:
        facts.append(f"year_built={addr['year_built']}")
    if addr.get("units") is not None:
        facts.append(f"units={addr['units']}")
    fact_s = ", ".join(facts) if facts else "limited parcel facts"
    return (
        f"Result={result} as_of={as_of.isoformat()}. {reason} "
        f"Facts: {fact_s}. Source {doc} retrieved {retr}."
    )


def evaluate_rule(rule: dict[str, Any], addr: dict[str, Any], as_of: date) -> tuple[str, str]:
    state = addr.get("state")
    city = addr.get("legal_city") or addr.get("city") or addr.get("postal_city")

    r_state = rule_state(rule)
    r_city = rule_city(rule)
    level = rule.get("level")
    if isinstance(rule.get("jurisdiction"), dict):
        level = rule["jurisdiction"].get("level") or level

    if r_state and r_state != state:
        return "out_of_jurisdiction", "Wrong state."
    if level == "city" and r_city and r_city != city:
        postal = addr.get("postal_city")
        if r_city != postal:
            return "out_of_jurisdiction", "City boundary."

    result = normalize_status(rule, as_of)
    if result in ("pending", "failed", "not_yet_effective"):
        return result, f"Legal status is {result}."

    cov = _coverage_dict(rule)
    if not cov and not isinstance(rule.get("coverage_conditions"), dict):
        return "applies", "No structured coverage test; jurisdiction match."

    coo = cov.get("certificate_of_occupancy_before") or cov.get(
        "max_certificate_of_occupancy"
    )
    if coo:
        yb = addr.get("year_built")
        cutoff = parse_date(coo)
        if yb is None:
            return "unknown", "Certificate-of-occupancy cutoff; year_built missing."
        if cutoff and yb > cutoff.year:
            return "not_covered", "Building after coverage cutoff."
        if cutoff and yb == cutoff.year:
            return "unknown", "year_built equals cutoff year; certificate date unknown."

    rolling = cov.get("rolling_age_years")
    if rolling is not None:
        yb = addr.get("year_built")
        if yb is None:
            return "unknown", f"Rolling {rolling}-year age test; year_built missing."
        age = as_of.year - int(yb)
        if age < int(rolling):
            return "not_covered", f"Building younger than {rolling} years."

    min_u = cov.get("min_units")
    if min_u is not None and addr.get("units") is None:
        return "unknown", "Rule depends on unit count; units missing in sample."

    max_u = cov.get("max_units")
    if max_u is not None and addr.get("units") is None:
        return "unknown", "Rule depends on unit count; units missing in sample."
    if max_u is not None and addr.get("units") is not None and addr["units"] > max_u:
        return "not_covered", f"Units exceed maximum ({max_u})."

    if cov.get("owner_type_exemption"):
        return "unknown", "Owner-occupied exemption may apply; owner not in public data."

    return "applies", "Coverage conditions satisfied or not applicable."


def apply_supersession(rows: list[dict], rules: list[dict]) -> list[dict]:
    by_id = {rule_id(r): r for r in rules}
    for row in rows:
        if row.get("result") != "applies":
            continue
        rule = by_id.get(row["team_rule_id"]) or {}
        for other_id in rule.get("overrides") or rule.get("supersedes_state_rule_ids") or []:
            interaction = (rule.get("interaction") or "").lower()
            if (
                "supersede" in interaction
                or "override" in interaction
                or "preempt" in interaction
                or rule.get("supersedes_state_rule_ids")
            ):
                for x in rows:
                    if x["team_rule_id"] == other_id and x["result"] == "applies":
                        x["result"] = "superseded"
                        x["explanation"] = (
                            x.get("explanation", "")
                            + f" Superseded by {row['team_rule_id']}."
                        )
    if any(r["team_rule_id"] == "SF-RENT-01" and r["result"] == "applies" for r in rows):
        for x in rows:
            if x["team_rule_id"] in {"CA-RENT-01", "CA-AB1482"} and x["result"] == "applies":
                x["result"] = "superseded"
    for x in rows:
        if x["team_rule_id"].startswith("LA-RSO") and x["result"] == "applies":
            for y in rows:
                if y["team_rule_id"] == "CA-RENT-01" and y["result"] == "applies":
                    y["result"] = "superseded"
    return rows


def lookup_address(
    addr: dict[str, Any], rules: list[dict[str, Any]], as_of_s: str
) -> dict[str, Any]:
    as_of = parse_date(as_of_s) or date(2026, 10, 1)
    rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []
    for rule in rules:
        result, reason = evaluate_rule(rule, addr, as_of)
        if result == "out_of_jurisdiction":
            continue
        if result in ("not_covered",):
            continue
        rid = rule_id(rule)
        expl = _explain(rule, addr, as_of, result, reason)
        if result == "failed":
            failed_rows.append(
                {
                    "team_rule_id": rid,
                    "category": rule.get("category"),
                    "result": "failed",
                    "citation": rule.get("citation"),
                    "quoted_span": rule.get("quoted_span"),
                    "explanation": expl,
                    "status": "failed",
                    "conflict_flag": bool(rule.get("conflict_flag")),
                }
            )
            continue
        rows.append(
            {
                "team_rule_id": rid,
                "category": rule.get("category"),
                "result": result,
                "citation": rule.get("citation") or rule.get("source_citation"),
                "quoted_span": rule.get("quoted_span"),
                "plain_language": rule.get("plain_en") or rule.get("requirement"),
                "plain_language_es": rule.get("plain_es"),
                "explanation": expl,
                "status": rule.get("status"),
                "effective_date": rule.get("effective_date"),
                "source_doc_id": rule.get("source_doc_id"),
                "source_url": rule.get("source_url"),
                "source_retrieved_at": rule.get("source_retrieved_at")
                or _manifest_retrieval(rule.get("source_doc_id")),
                "confidence": rule.get("confidence"),
                "conflict_flag": bool(rule.get("conflict_flag")),
                "conflict_note": rule.get("conflict_note"),
            }
        )
    rows = apply_supersession(rows, rules)
    return {
        "address_id": addr.get("address_id"),
        "street": addr.get("street") or addr.get("street_address"),
        "postal_city": addr.get("postal_city"),
        "legal_city": addr.get("legal_city"),
        "state": addr.get("state"),
        "as_of": as_of_s,
        "jurisdiction_stack": addr.get("jurisdiction_stack")
        or [addr.get("state"), addr.get("postal_city")],
        "disclaimer": "Not legal advice. For Hack-Nation demo / research only.",
        "rules": rows,
        "failed_or_not_applied": failed_rows,
    }
