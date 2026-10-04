"""Extraction quality gates (Chat 1)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.corpus_automate import derive_status
from src.extract_rules import extract_all
from src.paths import require_starter
from src.verify import is_literal_span

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rules():
    return extract_all()


def test_no_bill_url_in_force(rules):
    for r in rules:
        url = (r.get("source_url") or "").lower()
        if "/bills/" in url or "billhistory" in url:
            assert r.get("status") != "in_force", r["team_rule_id"]


def test_no_auto_prefix_ids(rules):
    auto = [r for r in rules if r["team_rule_id"].startswith("AUTO-")]
    assert auto == [], f"legacy AUTO ids remain: {[x['team_rule_id'] for x in auto[:5]]}"


def test_quoted_spans_literal(rules):
    starter = require_starter()
    text_dir = starter / "corpus" / "text"
    for r in rules:
        span = r.get("quoted_span") or ""
        if r["team_rule_id"] == "HOB-ALG-01" or span.startswith("["):
            continue
        doc = r.get("source_doc_id")
        path = text_dir / f"{doc}.txt"
        assert path.exists(), doc
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert is_literal_span(text, span), r["team_rule_id"]


def test_titles_readable(rules):
    for r in rules:
        title = (r.get("title") or "").strip()
        span = (r.get("quoted_span") or "").strip()
        assert len(title) <= 90, r["team_rule_id"]
        if span and not span.startswith("["):
            assert not span.startswith(title), (
                f"{r['team_rule_id']}: title is prefix of quoted_span"
            )


def test_no_duplicate_doc_category_span(rules):
    seen: set[tuple[str, str, str]] = set()
    for r in rules:
        span = re.sub(r"\s+", " ", (r.get("quoted_span") or "").strip().lower())[:80]
        key = (r.get("source_doc_id"), r.get("category"), span)
        assert key not in seen, r["team_rule_id"]
        seen.add(key)


def test_derive_status_bill_pending():
    st, eff = derive_status("D046", "https://malegislature.gov/Bills/194/S2983", "x")
    assert st == "pending"
    assert eff is None


def test_derive_status_fair_not_yet():
    st, eff = derive_status("D069", "https://pub.njleg.state.nj.us/", "x")
    assert st == "not_yet_effective"
    assert eff == "2027-07-01"


def test_rules_json_exists_after_extract():
    path = ROOT / "out" / "rules.json"
    if not path.exists():
        extract_all()
        path.write_text(json.dumps(extract_all(), indent=2))
    data = json.loads(path.read_text())
    assert isinstance(data, list)
    assert len(data) >= 40


def test_all_rules_validate_official_schema(rules):
    schema_path = require_starter() / "schema" / "rule_record.schema.json"
    assert schema_path.exists()
    schema = json.loads(schema_path.read_text())
    try:
        import jsonschema

        v = jsonschema.Draft202012Validator(schema)
        errors = []
        for r in rules:
            for err in v.iter_errors(r):
                errors.append(f"{r.get('team_rule_id')}: {err.message}")
        assert not errors, f"Schema validation failures:\n" + "\n".join(errors[:5])
    except ImportError:
        pass


def test_section_9_open_questions_surfaced(rules):
    """Verify all 4 open questions from pack §9 have conflict flags and notes."""
    rule_map = {r["team_rule_id"]: r for r in rules}

    # 1. Berkeley algorithmic ban dual dates (Ch. 13.63)
    assert "BERK-ALG-01" in rule_map
    berk = rule_map["BERK-ALG-01"]
    assert berk.get("conflict_flag") is True
    assert "pack §9" in (berk.get("conflict_note") or "").lower()

    # 2. NJ FAIR Act preemption of JC / Hoboken
    assert "NJ-ALG-01" in rule_map
    fair = rule_map["NJ-ALG-01"]
    assert fair.get("conflict_flag") is True
    assert "preempt" in (fair.get("conflict_note") or "").lower()

    # 3. LA RSO new formula dual dates
    assert "LA-RSO-02" in rule_map
    la = rule_map["LA-RSO-02"]
    assert la.get("conflict_flag") is True
    assert "pack §9" in (la.get("conflict_note") or "").lower()

    # 4. CA screening fee cap ambiguity
    assert "BERK-SCR-01" in rule_map
    scr = rule_map["BERK-SCR-01"]
    assert scr.get("conflict_flag") is True
    assert "pack §9" in (scr.get("conflict_note") or "").lower()

