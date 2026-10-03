"""Smoke tests for AppealPath Diff API fixtures."""

import sys
from pathlib import Path

API_SRC = Path(__file__).resolve().parents[1] / "apps" / "api" / "src"
sys.path.insert(0, str(API_SRC))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_deadline_miscalculation_flags_wrong_rule():
    samples = client.get("/api/samples").json()["samples"]
    case = next(s for s in samples if s["id"] == "case-03-deadline-miscalculation")
    r = client.post("/api/analyze", json={"notice_text": case["text"]})
    assert r.status_code == 200
    body = r.json()
    assert body["wrongful_application_detected"] is True
    assert body["statutory_window_days_current"] == 60
    assert "loop_iterations" in body
    assert len(body["loop_iterations"]) >= 3
    assert body["audit_trail"]["loop_cycle_count"] == len(body["loop_iterations"])
