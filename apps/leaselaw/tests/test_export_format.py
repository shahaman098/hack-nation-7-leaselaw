import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_lookups_submission_shape():
    path = ROOT / "out" / "lookups.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert "as_of" in data
    assert isinstance(data["lookups"], dict)
    assert len(data["lookups"]) == 500
    row = next(iter(data["lookups"].values()))
    assert {"team_rule_id", "result", "explanation", "conflict_flag"} <= set(row[0].keys())


def test_changes_submission_shape():
    path = ROOT / "out" / "changes.json"
    data = json.loads(path.read_text())
    for tid in ("T1", "T2", "T3", "T4", "T5"):
        assert tid in data
        assert "affected_address_ids" in data[tid]
        assert "notes" in data[tid]
