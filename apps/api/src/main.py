from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple, Literal
from datetime import date, datetime, timedelta, timezone
import hashlib
import re

from verify import (
    Check,
    extract_agency_claims,
    parse_date,
    run_checks,
    summarize_defects,
)

app = FastAPI(
    title="AppealPath Diff API",
    description="Administrative Time Machine: Temporal Rule-Diff & Evidence Delta Engine for Public Service Appeals",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Canonical Knowledge Base: Versioned Administrative Rules ---
RULES_DB = {
    "SNAP-MED-2025-V1": {
        "id": "SNAP-MED-2025-V1",
        "jurisdiction": "HHS / Municipal Social Services",
        "program": "Disability & Essential Medical Assistance (EMA)",
        "effective_from": "2024-01-01",
        "effective_to": "2025-06-30",
        "version_tag": "FY2024-2025 Guidance (Baseline)",
        "income_ceiling_single": 1825.0,
        "lookback_period_months": 3,
        "statutory_appeal_window_days": 30,
        "accepted_medical_signers": ["MD", "DO"],
        "required_evidence": [
            "Proof of residency (utility bill or lease within 60 days)",
            "3 consecutive paystubs or verified benefit award letter",
            "Physician Form MED-101 verifying impairment duration > 6 months"
        ],
        "clauses": [
            {
                "clause_id": "SEC-101.A",
                "title": "Categorical Income Threshold",
                "text": "Gross monthly household income for a single applicant shall not exceed $1,825.00 calculated over a three-month lookback period."
            },
            {
                "clause_id": "SEC-101.B",
                "title": "Medical Impairment Certification",
                "text": "The claimant must provide Form MED-101 executed by an MD/DO within the preceding 90 days certifying an impairment lasting at least 6 months."
            },
            {
                "clause_id": "SEC-102.C",
                "title": "Timeliness of Appeal",
                "text": "Administrative appeals must be postmarked or filed electronically within thirty (30) calendar days from the notice mailing date."
            }
        ]
    },
    "SNAP-MED-2025-V2": {
        "id": "SNAP-MED-2025-V2",
        "jurisdiction": "HHS / Municipal Social Services",
        "program": "Disability & Essential Medical Assistance (EMA)",
        "effective_from": "2025-07-01",
        "effective_to": "2026-03-31",
        "version_tag": "Mid-2025 Reform (Cost of Living Adjustment)",
        "income_ceiling_single": 1950.0,
        "lookback_period_months": 1,
        "statutory_appeal_window_days": 45,
        "accepted_medical_signers": ["MD", "DO", "PA", "APRN"],
        "required_evidence": [
            "Proof of residency (utility bill or digital address attestation within 90 days)",
            "1 prior month paystub or verified bank statement",
            "Physician Form MED-101 or Certified Nurse Practitioner (NP) endorsement"
        ],
        "clauses": [
            {
                "clause_id": "SEC-101.A",
                "title": "Categorical Income Threshold",
                "text": "Gross monthly household income for a single applicant shall not exceed $1,950.00 calculated based on the immediate 30-day prior month."
            },
            {
                "clause_id": "SEC-101.B",
                "title": "Medical Impairment Certification",
                "text": "The claimant may provide Form MED-101 executed by an MD/DO, Physician Assistant (PA), or Advanced Practice Registered Nurse (APRN)."
            },
            {
                "clause_id": "SEC-102.C",
                "title": "Timeliness of Appeal",
                "text": "Administrative appeals must be filed within forty-five (45) calendar days from the notice date."
            }
        ]
    },
    "SNAP-MED-2026-CURRENT": {
        "id": "SNAP-MED-2026-CURRENT",
        "jurisdiction": "HHS / Municipal Social Services",
        "program": "Disability & Essential Medical Assistance (EMA)",
        "effective_from": "2026-04-01",
        "effective_to": "2027-12-31",
        "version_tag": "2026 Modernized Administrative Standard",
        "income_ceiling_single": 2100.0,
        "lookback_period_months": 1,
        "statutory_appeal_window_days": 60,
        "accepted_medical_signers": ["MD", "DO", "PA", "APRN"],
        "required_evidence": [
            "Proof of residency (digital tax/utility record)",
            "1 prior month income statement with automatic 20% medical expense deduction allowance",
            "Form MED-101 or electronic health record (EHR) functional limitation summary"
        ],
        "clauses": [
            {
                "clause_id": "SEC-101.A",
                "title": "Categorical Income Threshold",
                "text": "Gross monthly household income for a single applicant shall not exceed $2,100.00 with allowable standard out-of-pocket medical expense deduction."
            },
            {
                "clause_id": "SEC-101.B",
                "title": "Medical Impairment Certification",
                "text": "Claimant may substantiate impairment through signed Form MED-101 or certified Fast Healthcare Interoperability Resources (FHIR) clinic export."
            },
            {
                "clause_id": "SEC-102.C",
                "title": "Timeliness of Appeal",
                "text": "Administrative appeals must be filed within sixty (60) calendar days from the date stamped on the denial notice."
            }
        ]
    }
}

# --- Sample Decision Notices ---
SAMPLE_NOTICES = [
    {
        "id": "case-01-income-lookback",
        "title": "Notice of Denial: Medical Assistance (Decision Date: 2025-05-12)",
        "case_number": "MA-2025-88391",
        "claimant_name": "Eleanor Vance",
        "notice_date": "2025-05-12",
        "denial_reason": "Excess income reported ($1,890.00/mo over 3-month average) under SEC-101.A.",
        "text": """OFFICIAL NOTICE OF ADVERSE DETERMINATION
Case Number: MA-2025-88391
Claimant: Eleanor Vance
Date of Notice: May 12, 2025

Dear Ms. Vance,
Your application for Essential Medical Assistance (EMA) filed on April 10, 2025 is hereby DENIED.
REASON: Gross monthly income was evaluated across February, March, and April 2025, yielding an average monthly gross of $1,890.00, which exceeds the statutory ceiling of $1,825.00 under Section 101.A.
APPEAL RIGHTS: If you disagree, you must file a formal notice of appeal within 30 days of this notice (deadline: June 11, 2025)."""
    },
    {
        "id": "case-02-np-signature",
        "title": "Notice of Denial: Medical Impairment Proof (Decision Date: 2025-08-20)",
        "case_number": "EMA-2025-10492",
        "claimant_name": "Marcus Chen",
        "notice_date": "2025-08-20",
        "denial_reason": "Medical evaluation submitted was signed by a Nurse Practitioner, which was rejected by processing officer citing SEC-101.B.",
        "text": """OFFICIAL NOTICE OF ACTION
Case ID: EMA-2025-10492
Applicant: Marcus Chen
Mailing Date: August 20, 2025

Notice is given that Medical Assistance benefits are DENIED.
FINDINGS: The medical disability report submitted on July 28, 2025 was completed and signed by an Advanced Practice Registered Nurse (APRN), rather than a licensed Physician (MD/DO) as required under guidance Section 101.B.
You have 45 days from the mailing date of this letter to request an administrative fair hearing."""
    },
    {
        "id": "case-03-deadline-miscalculation",
        "title": "Notice of Late Appeal Dismissal (Decision Date: 2026-05-10)",
        "case_number": "SEC-2026-44012",
        "claimant_name": "Devon Robinson",
        "notice_date": "2026-05-10",
        "denial_reason": "Caseworker dismissed appeal filed 38 days after notice, believing 30-day rule still applied.",
        "text": """ADMINISTRATIVE DISMISSAL NOTICE
Case Number: SEC-2026-44012
Recipient: Devon Robinson
Decision Date: May 10, 2026

Your appeal filed on June 17, 2026 (38 days post-notice) is dismissed as untimely. Administrative procedures strictly require notice of appeal within 30 calendar days."""
    }
]

# --- Pydantic Models ---
class AnalyzeRequest(BaseModel):
    notice_text: str = Field(..., description="Full text or extract of the administrative decision letter")
    notice_date: Optional[str] = Field(None, description="Optional override date YYYY-MM-DD")

class ClauseDiff(BaseModel):
    clause_id: str
    title: str
    decision_version_text: str
    current_version_text: str
    has_changed: bool
    impact_note: str

class EvidenceItem(BaseModel):
    requirement: str
    is_missing_or_vulnerable: bool
    actionable_remedy: str

class LoopIteration(BaseModel):
    iteration: int
    stage: str
    target: str
    result: Literal["pass", "fail", "adjusted"]
    feedback: str

class AnalysisResult(BaseModel):
    case_number: Optional[str]
    claimant_name: Optional[str]
    decision_date: str
    governing_rule_version: str
    current_rule_version: str
    statutory_window_days_applied: int
    statutory_window_days_current: int
    statutory_window_days_agency: Optional[int]
    appeal_filing_deadline: str
    days_remaining_or_overdue: int
    wrongful_application_detected: bool
    wrongful_application_summary: Optional[str]
    clause_diffs: List[ClauseDiff]
    required_evidence_checklist: List[EvidenceItem]
    checks: List[Check]
    loop_iterations: List[LoopIteration] = Field(default_factory=list)
    audit_trail: Dict[str, Any]

# --- Helper Functions ---
def find_governing_rule(dt_str: Optional[str]) -> Optional[Dict[str, Any]]:
    if not dt_str:
        return None
    target_date = parse_date(dt_str)
    if target_date is None:
        return None

    for rule in RULES_DB.values():
        start = datetime.strptime(rule["effective_from"], "%Y-%m-%d").date()
        end = datetime.strptime(rule["effective_to"], "%Y-%m-%d").date()
        if start <= target_date <= end:
            return rule
    return None


def extract_notice_metadata(
    text: str, fallback_date: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    case_match = re.search(r"Case (?:Number|ID):\s*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    case_number = case_match.group(1) if case_match else None

    name_match = re.search(r"(?:Claimant|Applicant|Recipient):\s*([^\n\r]+)", text, re.IGNORECASE)
    claimant_name = name_match.group(1).strip() if name_match else None

    extracted_date: Optional[str] = None
    if fallback_date:
        if parse_date(fallback_date):
            extracted_date = fallback_date
    else:
        date_match = re.search(
            r"(?:Date of Notice|Mailing Date|Decision Date):\s*([^\n\r]+)",
            text,
            re.IGNORECASE,
        )
        if date_match:
            raw_dt = date_match.group(1).strip()
            parsed = parse_date(raw_dt)
            if parsed:
                extracted_date = parsed.strftime("%Y-%m-%d")

    return case_number, claimant_name, extracted_date


def _checks_passed_label(checks: List[Check]) -> str:
    non_skip = [c for c in checks if c.status != "skip"]
    passed = sum(1 for c in non_skip if c.status == "pass")
    return f"{passed}/{len(non_skip)}"


def _unverified_response(checks: List[Check]) -> None:
    raise HTTPException(
        status_code=422,
        detail={
            "status": "UNVERIFIED",
            "checks": [c.model_dump() for c in checks],
        },
    )

# --- Endpoints ---

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AppealPath Diff Engine", "rules_indexed": len(RULES_DB)}

@app.get("/api/samples")
def get_samples():
    return {"samples": SAMPLE_NOTICES}

@app.get("/api/rules")
def get_rules():
    return {"rules": list(RULES_DB.values())}

@app.post("/api/analyze", response_model=AnalysisResult)
def analyze_notice(req: AnalyzeRequest):
    claims = extract_agency_claims(req.notice_text)
    case_number, claimant_name, decision_date = extract_notice_metadata(
        req.notice_text, req.notice_date
    )
    governing_rule = find_governing_rule(decision_date)
    checks = run_checks(decision_date, governing_rule, claims)

    if any(c.blocking and c.status == "fail" for c in checks):
        _unverified_response(checks)

    assert governing_rule is not None and decision_date is not None
    current_rule = RULES_DB["SNAP-MED-2026-CURRENT"]

    dec_dt = parse_date(decision_date)
    assert dec_dt is not None
    deadline_days = governing_rule["statutory_appeal_window_days"]
    statutory_deadline = dec_dt + timedelta(days=deadline_days)

    today = date(2026, 10, 3)
    days_remaining = (statutory_deadline - today).days

    clause_diffs = []
    gov_clauses = {c["clause_id"]: c for c in governing_rule["clauses"]}
    cur_clauses = {c["clause_id"]: c for c in current_rule["clauses"]}

    for cid, g_clause in gov_clauses.items():
        c_clause = cur_clauses.get(cid, g_clause)
        changed = g_clause["text"] != c_clause["text"]
        impact = ""
        if cid == "SEC-101.A":
            impact = f"Income limit changed from ${governing_rule['income_ceiling_single']:.2f} to ${current_rule['income_ceiling_single']:.2f}. Lookback period shifted to 30 days."
        elif cid == "SEC-101.B":
            impact = "Provider qualification expanded to include APRN/PA and direct EHR data."
        elif cid == "SEC-102.C":
            impact = f"Appeal window expanded from {governing_rule['statutory_appeal_window_days']} days to {current_rule['statutory_appeal_window_days']} days."

        clause_diffs.append(ClauseDiff(
            clause_id=cid,
            title=g_clause["title"],
            decision_version_text=g_clause["text"],
            current_version_text=c_clause["text"],
            has_changed=changed,
            impact_note=impact
        ))

    wrongful_application_detected = any(c.status == "fail" for c in checks)
    wrongful_application_summary = summarize_defects(checks)

    checklist: List[EvidenceItem] = [
        EvidenceItem(
            requirement=req_text,
            is_missing_or_vulnerable=True,
            actionable_remedy=f"Obtain and attach: {req_text}",
        )
        for req_text in governing_rule["required_evidence"]
    ]
    checklist.append(
        EvidenceItem(
            requirement=f"Notice of Appeal signed within governing statutory window ({deadline_days} days)",
            is_missing_or_vulnerable=False,
            actionable_remedy=f"Generate Form AP-900 with statutory citation to {governing_rule['id']} SEC-102.C.",
        )
    )

    loop_iterations: List[LoopIteration] = []

    # Iteration 1: Parse & Validate Notice Grounding
    if decision_date:
        loop_iterations.append(
            LoopIteration(
                iteration=1,
                stage="Notice Ingestion & Grounding",
                target="decision_date",
                result="pass",
                feedback=f"Successfully anchored decision date to {decision_date}.",
            )
        )
    else:
        loop_iterations.append(
            LoopIteration(
                iteration=1,
                stage="Notice Ingestion & Grounding",
                target="decision_date",
                result="fail",
                feedback="Unanchored decision date; cannot ground rule without temporal baseline.",
            )
        )

    # Iteration 2: Temporal Corpus Lookup & Validation
    if governing_rule is not None:
        loop_iterations.append(
            LoopIteration(
                iteration=2,
                stage="Corpus Rule Evaluation",
                target="governing_rule",
                result="pass",
                feedback=(
                    f"Verified temporal match {governing_rule['id']} "
                    f"[{governing_rule['effective_from']} to {governing_rule['effective_to']}]."
                ),
            )
        )
    else:
        loop_iterations.append(
            LoopIteration(
                iteration=2,
                stage="Corpus Rule Evaluation",
                target="governing_rule",
                result="fail",
                feedback="No statutory corpus coverage for provided date.",
            )
        )

    # Iteration 3: Agency Defense / Defect Evaluator Check
    failed_checks = [c for c in checks if c.status == "fail" and not c.blocking]
    if failed_checks:
        loop_iterations.append(
            LoopIteration(
                iteration=3,
                stage="Agency Defect Evaluator",
                target="statutory_admissibility",
                result="fail",
                feedback=(
                    f"Flagged {len(failed_checks)} unlawful agency deviations. "
                    f"Optimizer: Synthesizing statutory defense & evidence delta."
                ),
            )
        )
        loop_iterations.append(
            LoopIteration(
                iteration=4,
                stage="Appeal Remedy Optimizer",
                target="remedy_synthesis",
                result="adjusted",
                feedback=(
                    f"Adjusted appeal window from agency-claimed {claims.window_days or 'unspecified'} days "
                    f"to statutory {deadline_days} days under {governing_rule['id']} SEC-102.C. "
                    "Generated required evidentiary checklist."
                ),
            )
        )
    else:
        loop_iterations.append(
            LoopIteration(
                iteration=3,
                stage="Agency Defect Evaluator",
                target="statutory_admissibility",
                result="pass",
                feedback="Agency decision conforms with governing standard. No unlawful procedural defect found.",
            )
        )

    notice_hash = hashlib.sha256(req.notice_text.encode()).hexdigest()
    audit_trail = {
        "engine": "AppealPath Diff v1.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hash_verification": f"sha256-{notice_hash}",
        "statutory_corpus_snapshot": governing_rule["version_tag"],
        "checks_passed": _checks_passed_label(checks),
        "loop_cycle_count": len(loop_iterations),
    }

    return AnalysisResult(
        case_number=case_number,
        claimant_name=claimant_name,
        decision_date=decision_date,
        governing_rule_version=f"{governing_rule['id']} ({governing_rule['version_tag']})",
        current_rule_version=f"{current_rule['id']} ({current_rule['version_tag']})",
        statutory_window_days_applied=deadline_days,
        statutory_window_days_current=current_rule["statutory_appeal_window_days"],
        statutory_window_days_agency=claims.window_days,
        appeal_filing_deadline=statutory_deadline.strftime("%Y-%m-%d"),
        days_remaining_or_overdue=days_remaining,
        wrongful_application_detected=wrongful_application_detected,
        wrongful_application_summary=wrongful_application_summary,
        clause_diffs=clause_diffs,
        required_evidence_checklist=checklist,
        checks=checks,
        loop_iterations=loop_iterations,
        audit_trail=audit_trail
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
