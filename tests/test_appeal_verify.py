"""Verification layer tests for AppealPath Diff."""

import hashlib
import sys
from pathlib import Path

API_SRC = Path(__file__).resolve().parents[1] / "apps" / "api" / "src"
sys.path.insert(0, str(API_SRC))

from fastapi.testclient import TestClient  # noqa: E402
from main import SAMPLE_NOTICES, AnalyzeRequest, analyze_notice, app  # noqa: E402
import cli  # noqa: E402

client = TestClient(app)


def _check_by_name(body: dict, name: str) -> dict:
    return next(c for c in body["checks"] if c["name"] == name)


def test_garbage_notice_api_unverified():
    r = client.post("/api/analyze", json={"notice_text": "hello this is not a notice"})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["status"] == "UNVERIFIED"
    assert _check_by_name(detail, "decision_date_parsed")["status"] == "fail"


def test_garbage_notice_cli_exit_2():
    assert cli.main(["--text", "hello this is not a notice"]) == 2


def test_decision_date_outside_rules_unverified():
    text = """Case Number: OLD-1
Claimant: Test User
Decision Date: 2023-01-15
Appeal within 30 days."""
    r = client.post("/api/analyze", json={"notice_text": text})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert _check_by_name(detail, "governing_rule_found")["status"] == "fail"


def test_may_2026_45_day_dismissal_flagged():
    text = """Case Number: X-2026
Recipient: Jane Doe
Decision Date: May 10, 2026
You have 45 days to appeal. Dismissed as untimely."""
    r = client.post("/api/analyze", json={"notice_text": text})
    assert r.status_code == 200
    body = r.json()
    assert body["wrongful_application_detected"] is True
    window = _check_by_name(body, "appeal_window_matches_rule")
    assert window["status"] == "fail"
    assert window["expected"] == "60"
    assert window["observed"] == "45"


def test_case_03_window_and_filing_checks():
    case = next(s for s in SAMPLE_NOTICES if s["id"] == "case-03-deadline-miscalculation")
    res = analyze_notice(AnalyzeRequest(notice_text=case["text"]))
    assert res.statutory_window_days_agency == 30
    assert _check_by_name(res.model_dump(), "appeal_window_matches_rule")["status"] == "fail"
    assert _check_by_name(res.model_dump(), "appeal_filed_within_window")["status"] == "fail"


def test_case_02_provider_signer_fails():
    case = next(s for s in SAMPLE_NOTICES if s["id"] == "case-02-np-signature")
    res = analyze_notice(AnalyzeRequest(notice_text=case["text"]))
    assert _check_by_name(res.model_dump(), "provider_signer_accepted")["status"] == "fail"
    assert res.wrongful_application_detected is True


def test_case_01_not_flagged():
    case = next(s for s in SAMPLE_NOTICES if s["id"] == "case-01-income-lookback")
    res = analyze_notice(AnalyzeRequest(notice_text=case["text"]))
    assert res.wrongful_application_detected is False
    for c in res.checks:
        assert c.status in ("pass", "skip")


def test_audit_hash_stable_sha256():
    case = SAMPLE_NOTICES[0]["text"]
    r1 = analyze_notice(AnalyzeRequest(notice_text=case))
    r2 = analyze_notice(AnalyzeRequest(notice_text=case))
    expected = f"sha256-{hashlib.sha256(case.encode()).hexdigest()}"
    assert r1.audit_trail["hash_verification"] == expected
    assert r2.audit_trail["hash_verification"] == expected


def test_checklist_uses_required_evidence():
    case = next(s for s in SAMPLE_NOTICES if s["id"] == "case-01-income-lookback")
    res = analyze_notice(AnalyzeRequest(notice_text=case["text"]))
    from main import RULES_DB

    governing = RULES_DB["SNAP-MED-2025-V1"]
    for req in governing["required_evidence"]:
        assert any(item.requirement == req for item in res.required_evidence_checklist)
    assert len(res.required_evidence_checklist) == 4
