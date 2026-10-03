def test_health_endpoint():
    from main import health
    res = health()
    assert res["status"] == "ok"
    assert res["rules_indexed"] == 3

def test_sample_notice_extraction():
    from main import SAMPLE_NOTICES, extract_notice_metadata
    case_num, name, dt = extract_notice_metadata(SAMPLE_NOTICES[0]["text"])
    assert case_num == "MA-2025-88391"
    assert name == "Eleanor Vance"
    assert dt == "2025-05-12"

def test_wrongful_denial_aprn_detection():
    from main import SAMPLE_NOTICES, AnalyzeRequest, analyze_notice
    req = AnalyzeRequest(notice_text=SAMPLE_NOTICES[1]["text"])
    res = analyze_notice(req)
    assert res.wrongful_application_detected is True
    assert "CRITICAL LEGAL DEFECT" in res.wrongful_application_summary
    assert res.governing_rule_version.startswith("SNAP-MED-2025-V2")
    assert len(res.clause_diffs) == 3
    assert len(res.required_evidence_checklist) == 4

def test_wrongful_deadline_dismissal():
    from main import SAMPLE_NOTICES, AnalyzeRequest, analyze_notice
    req = AnalyzeRequest(notice_text=SAMPLE_NOTICES[2]["text"])
    res = analyze_notice(req)
    assert res.wrongful_application_detected is True
    assert "unlawful" in res.wrongful_application_summary.lower()
    assert res.statutory_window_days_applied == 60
