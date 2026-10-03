"""Deterministic verification of agency claims against the rules corpus."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel

DATE_FORMATS = ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"]


class Check(BaseModel):
    name: str
    status: Literal["pass", "fail", "skip"]
    blocking: bool
    expected: Optional[str] = None
    observed: Optional[str] = None
    detail: str


@dataclass
class AgencyClaims:
    window_days: Optional[int] = None
    cited_clause: Optional[str] = None
    filed_date: Optional[date] = None
    signer_type: Optional[str] = None
    dismissed_untimely: bool = False


def parse_date(raw: str) -> Optional[date]:
    text = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def extract_agency_claims(text: str) -> AgencyClaims:
    window_days: Optional[int] = None
    window_match = re.search(
        r"(?:within|have)\s+(\d+)\s+(?:calendar\s+)?days",
        text,
        re.IGNORECASE,
    )
    if window_match:
        window_days = int(window_match.group(1))

    cited_clause: Optional[str] = None
    clause_match = re.search(
        r"(?:Section|SEC-)\s*(\d{3}\.[A-Z])",
        text,
        re.IGNORECASE,
    )
    if clause_match:
        cited_clause = f"SEC-{clause_match.group(1).upper()}"

    filed_date: Optional[date] = None
    filed_match = re.search(
        r"appeal filed on\s+([^\n\r(]+)",
        text,
        re.IGNORECASE,
    )
    if filed_match:
        filed_date = parse_date(filed_match.group(1).strip())

    signer_type: Optional[str] = None
    if re.search(r"APRN|Nurse Practitioner", text, re.IGNORECASE):
        signer_type = "APRN"
    elif re.search(r"Physician Assistant|\bPA\b", text, re.IGNORECASE):
        signer_type = "PA"

    dismissed_untimely = "untimely" in text.lower()

    return AgencyClaims(
        window_days=window_days,
        cited_clause=cited_clause,
        filed_date=filed_date,
        signer_type=signer_type,
        dismissed_untimely=dismissed_untimely,
    )


def _skip(name: str, blocking: bool, detail: str) -> Check:
    return Check(
        name=name,
        status="skip",
        blocking=blocking,
        expected=None,
        observed=None,
        detail=detail,
    )


def run_checks(
    decision_date: Optional[str],
    governing_rule: Optional[Dict[str, Any]],
    claims: AgencyClaims,
) -> List[Check]:
    checks: List[Check] = []

    if decision_date and parse_date(decision_date) is not None:
        checks.append(
            Check(
                name="decision_date_parsed",
                status="pass",
                blocking=True,
                expected="valid YYYY-MM-DD decision date",
                observed=decision_date,
                detail="Decision date extracted and parsed.",
            )
        )
    else:
        checks.append(
            Check(
                name="decision_date_parsed",
                status="fail",
                blocking=True,
                expected="valid YYYY-MM-DD decision date",
                observed=decision_date,
                detail="No parseable decision date found in notice.",
            )
        )

    if governing_rule is not None:
        checks.append(
            Check(
                name="governing_rule_found",
                status="pass",
                blocking=True,
                expected=f"rule effective on {decision_date}",
                observed=governing_rule["id"],
                detail="Governing rule version located for decision date.",
            )
        )
    else:
        checks.append(
            Check(
                name="governing_rule_found",
                status="fail",
                blocking=True,
                expected="rule covering decision date",
                observed=None,
                detail="No statutory rule version covers the decision date.",
            )
        )

    if governing_rule is None:
        return checks

    if claims.cited_clause:
        clause_ids = {c["clause_id"] for c in governing_rule["clauses"]}
        if claims.cited_clause in clause_ids:
            checks.append(
                Check(
                    name="cited_clause_exists",
                    status="pass",
                    blocking=False,
                    expected=claims.cited_clause,
                    observed=claims.cited_clause,
                    detail="Cited clause exists in governing rule.",
                )
            )
        else:
            checks.append(
                Check(
                    name="cited_clause_exists",
                    status="fail",
                    blocking=False,
                    expected=f"clause in {governing_rule['id']}",
                    observed=claims.cited_clause,
                    detail=f"Cited clause {claims.cited_clause} not found in governing rule.",
                )
            )
    else:
        checks.append(
            _skip(
                "cited_clause_exists",
                False,
                "No clause citation detected in notice.",
            )
        )

    statutory_days = governing_rule["statutory_appeal_window_days"]
    if claims.window_days is not None:
        if claims.window_days == statutory_days:
            checks.append(
                Check(
                    name="appeal_window_matches_rule",
                    status="pass",
                    blocking=False,
                    expected=str(statutory_days),
                    observed=str(claims.window_days),
                    detail="Agency-stated appeal window matches governing rule.",
                )
            )
        else:
            checks.append(
                Check(
                    name="appeal_window_matches_rule",
                    status="fail",
                    blocking=False,
                    expected=str(statutory_days),
                    observed=str(claims.window_days),
                    detail=(
                        f"Agency applied a {claims.window_days}-day appeal window; "
                        f"governing rule SEC-102.C requires {statutory_days} days — unlawful."
                    ),
                )
            )
    else:
        checks.append(
            _skip(
                "appeal_window_matches_rule",
                False,
                "No appeal window duration stated in notice.",
            )
        )

    if claims.dismissed_untimely and claims.filed_date and decision_date:
        dec_dt = parse_date(decision_date)
        if dec_dt is not None:
            days_after = (claims.filed_date - dec_dt).days
            if days_after <= statutory_days:
                checks.append(
                    Check(
                        name="appeal_filed_within_window",
                        status="fail",
                        blocking=False,
                        expected=f"filed within {statutory_days} days",
                        observed=f"filed day {days_after}",
                        detail=(
                            f"Appeal filed {days_after} days after notice, within the "
                            f"{statutory_days}-day statutory window — untimely dismissal is unlawful."
                        ),
                    )
                )
            else:
                checks.append(
                    Check(
                        name="appeal_filed_within_window",
                        status="pass",
                        blocking=False,
                        expected=f"filed within {statutory_days} days",
                        observed=f"filed day {days_after}",
                        detail="Appeal filed after statutory window; dismissal may be valid.",
                    )
                )
        else:
            checks.append(
                _skip(
                    "appeal_filed_within_window",
                    False,
                    "Cannot compute filing timeliness without decision date.",
                )
            )
    else:
        checks.append(
            _skip(
                "appeal_filed_within_window",
                False,
                "No untimely dismissal with filing date to verify.",
            )
        )

    if claims.signer_type:
        accepted = governing_rule.get("accepted_medical_signers", [])
        if claims.signer_type in accepted:
            checks.append(
                Check(
                    name="provider_signer_accepted",
                    status="fail",
                    blocking=False,
                    expected=f"signer {claims.signer_type} accepted under SEC-101.B",
                    observed=f"agency rejected {claims.signer_type}",
                    detail=(
                        f"Governing rule accepts {claims.signer_type} medical endorsements; "
                        "denial on physician-only grounds is unlawful."
                    ),
                )
            )
        else:
            checks.append(
                Check(
                    name="provider_signer_accepted",
                    status="pass",
                    blocking=False,
                    expected=f"signer not in {accepted}",
                    observed=claims.signer_type,
                    detail="Signer type not authorized under governing rule.",
                )
            )
    else:
        checks.append(
            _skip(
                "provider_signer_accepted",
                False,
                "No medical signer type referenced in notice.",
            )
        )

    return checks


def summarize_defects(checks: List[Check]) -> Optional[str]:
    failed = [c for c in checks if c.status == "fail"]
    if not failed:
        return None
    parts = [c.detail for c in failed]
    return "CRITICAL LEGAL DEFECT: " + " ".join(parts)
