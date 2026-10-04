from datetime import date

from src.engine import evaluate_rule, lookup_address, parse_date
from src.jurisdiction import attach_legal_city


def _addr(**kwargs):
    base = {
        "address_id": "X1",
        "state": "CA",
        "postal_city": "San Francisco",
        "legal_city": "San Francisco",
        "year_built": 1962,
        "units": 10,
    }
    base.update(kwargs)
    return base


def test_parse_date():
    assert parse_date("2026-10-01") == date(2026, 10, 1)


def test_sf_rent_unknown_on_cutoff_year():
    rule = {
        "team_rule_id": "SF-RENT-01",
        "jurisdiction": "San Francisco, CA",
        "level": "city",
        "category": "rent_increase_limits",
        "status": "in_force",
        "coverage_conditions": {"certificate_of_occupancy_before": "1979-06-13"},
    }
    addr = _addr(year_built=1979)
    result, _ = evaluate_rule(rule, addr, date(2026, 10, 1))
    assert result == "unknown"


def test_san_ysidro_maps_to_san_diego():
    raw = {
        "address_id": "Z9",
        "street_address": "1 Main",
        "postal_city": "San Ysidro",
        "state": "CA",
        "zip": "92173",
    }
    addr = attach_legal_city(raw)
    assert addr["legal_city"] == "San Diego"


def test_failed_rule_in_failed_section():
    rules = [
        {
            "team_rule_id": "MA-RENT-P1",
            "jurisdiction": "MA",
            "level": "state",
            "category": "rent_increase_limits",
            "status": "failed",
            "requirement": "Ballot struck",
            "citation": "test",
            "source_url": "https://example.com",
            "quoted_span": "x" * 25,
        }
    ]
    out = lookup_address(_addr(state="MA", postal_city="Boston", legal_city="Boston"), rules, "2026-10-01")
    assert not any(r["team_rule_id"] == "MA-RENT-P1" for r in out["rules"])
    assert any(r["team_rule_id"] == "MA-RENT-P1" for r in out["failed_or_not_applied"])
