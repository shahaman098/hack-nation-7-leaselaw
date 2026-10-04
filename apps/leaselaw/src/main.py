from __future__ import annotations

import json
from pathlib import Path

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .data import load_addresses, load_change_tests, load_rules, starter_stats
from .engine import lookup_address
from .ui_html import _LOGO, home_page, pipeline_page_html

_APP_ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(
    title="LeaseLaw Navigator",
    description="Hack-Nation 7 Track 02 — RealPage. Not legal advice.",
    version="0.4.0",
)

app.mount("/static", StaticFiles(directory=_APP_ROOT / "static"), name="static")

_OUT = _APP_ROOT / "out"
_AUDIT_LOG = _OUT / "audit" / "lookup_log.jsonl"


def _log_lookup(address_id: str, as_of: str) -> None:
    _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "address_id": address_id,
        "as_of": as_of,
    }
    with _AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


@app.get("/health")
def health() -> dict:
    try:
        stats = starter_stats()
    except FileNotFoundError as e:
        stats = {"error": str(e)}
    return {
        "ok": True,
        "track": "02-realpage",
        "rules": len(load_rules()),
        "addresses": len(load_addresses()),
        "starter": stats,
    }


@app.get("/api/addresses")
def list_addresses(
    limit: int = 50, state: str | None = None, q: str | None = None
) -> list[dict]:
    rows = load_addresses()
    if state:
        rows = [a for a in rows if a.get("state") == state.upper()]
    if q:
        ql = q.lower().strip()
        rows = [
            a
            for a in rows
            if ql in f"{a.get('address_id','')} {a.get('street_address','')} {a.get('street','')} "
            f"{a.get('postal_city','')} {a.get('legal_city','')} {a.get('state','')}".lower()
        ]
    return rows[: max(1, min(limit, 500))]


@app.get("/out/{filename}")
def download_artifact(filename: str):
    allowed = {"rules.json", "lookups.json", "changes.json", "eval-report.json"}
    if filename not in allowed:
        raise HTTPException(404)
    path = _OUT / filename
    if not path.exists():
        raise HTTPException(404, "artifact missing — run export_outputs")
    return FileResponse(path, media_type="application/json", filename=filename)


@app.get("/api/change-tests")
def api_change_tests() -> list[dict]:
    return load_change_tests()


@app.get("/api/open-questions")
def api_open_questions() -> dict:
    """Surfaces the four known open legal questions from starter pack §9."""
    rules = load_rules()
    by_id = {r["team_rule_id"]: r for r in rules}
    return {
        "count": 4,
        "disclaimer": "Not legal advice. For hackathon research and prototype demonstration only.",
        "questions": [
            {
                "id": "berkeley-dual-dates",
                "topic": "Berkeley Algorithmic Ban Dual Effective Dates",
                "team_rule_id": "BERK-ALG-01",
                "jurisdiction": "Berkeley, CA",
                "citation": by_id.get("BERK-ALG-01", {}).get("citation", "Berkeley Ord. §13.63.030"),
                "sample_address_id": "A0005",
                "published_dates": ["2026-03-01 (Ordinance text)", "2026-01-01 (Law firm bulletin)"],
                "explanation": (
                    "Berkeley's algorithmic rent-setting ban (ch. 13.63) has two published "
                    "effective dates: March 1, 2026 in the enacted ordinance text versus January 2026 "
                    "per an August 2026 legal practice bulletin. LeaseLaw surfaces this conflict flag "
                    "for human compliance review."
                ),
                "conflict_note": by_id.get("BERK-ALG-01", {}).get("conflict_note"),
            },
            {
                "id": "nj-fair-preemption",
                "topic": "New Jersey FAIR Act Preemption of Local Ordinances",
                "team_rule_id": "NJ-ALG-01",
                "jurisdiction": "NJ (Hoboken / Jersey City)",
                "citation": by_id.get("NJ-ALG-01", {}).get("citation", "NJ FAIR Act, P.L.2026, c.43"),
                "sample_address_id": "A0002",
                "effective_date": "2027-07-01",
                "explanation": (
                    "New Jersey's statewide FAIR Act (enacted 2026-07-20, effective 2027-07-01) "
                    "may preempt preexisting municipal algorithmic-rent bans in Hoboken and Jersey City. "
                    "LeaseLaw tags affected Hoboken and Jersey City properties with conflict flags."
                ),
                "conflict_note": by_id.get("NJ-ALG-01", {}).get("conflict_note"),
            },
            {
                "id": "la-rso-dual-dates",
                "topic": "Los Angeles New RSO Formula Dual Effective Dates",
                "team_rule_id": "LA-RSO-02",
                "jurisdiction": "Los Angeles, CA",
                "citation": by_id.get("LA-RSO-02", {}).get("citation", "LAHD RSO Calculator"),
                "sample_address_id": "A0001",
                "published_dates": ["2026-02-02 (LAHD)", "2026-01-24 (Landlord Association)"],
                "explanation": (
                    "Los Angeles's new RSO formula has two published effective dates: 2026-02-02 "
                    "per LAHD official guidelines vs 2026-01-24 per landlord association notices. "
                    "LeaseLaw flags properties in Los Angeles subject to RSO with this ambiguity."
                ),
                "conflict_note": by_id.get("LA-RSO-02", {}).get("conflict_note"),
            },
            {
                "id": "ca-screening-fee-cap",
                "topic": "California Screening-Fee Cap Statutory Ambiguity",
                "team_rule_id": "BERK-SCR-01",
                "jurisdiction": "Berkeley / California",
                "citation": by_id.get("BERK-SCR-01", {}).get("citation", "Cal. Civ. Code §1950.6 / BMC §13.78.010"),
                "sample_address_id": "A0005",
                "explanation": (
                    "California's screening-fee cap under Cal. Civ. Code § 1950.6 has no single official "
                    "2026 dollar figure published statewide; municipal ordinances like Berkeley explicitly cap "
                    "at $68.96 while inflation adjustments vary across court jurisdictions."
                ),
                "conflict_note": by_id.get("BERK-SCR-01", {}).get("conflict_note"),
            },
        ],
    }


@app.get("/api/eval")
def api_eval() -> dict:
    """Judge-visible stand-in until official score.py is in the pack."""
    path = _OUT / "eval-report.json"
    if not path.exists():
        return {
            "passed": 0,
            "total": 0,
            "change_tests": [],
            "note": "Run: python -m src.eval_harness",
            "official_score_py": False,
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    data["official_score_py"] = False
    data["note"] = (
        "Harness T1–T5 (participant no-scoring pack has no score.py). "
        "Not an official RealPage score."
    )
    return data


@app.get("/api/lookup")
def api_lookup(
    address_id: str = Query(...),
    as_of: str = Query("2026-10-01"),
) -> dict:
    addresses = {a["address_id"]: a for a in load_addresses()}
    if address_id not in addresses:
        raise HTTPException(404, f"unknown address_id {address_id}")
    _log_lookup(address_id, as_of)
    return lookup_address(addresses[address_id], load_rules(), as_of)


@app.get("/api/audit/{address_id}")
def api_audit(address_id: str, as_of: str = Query("2026-10-01")) -> dict:
    addresses = {a["address_id"]: a for a in load_addresses()}
    if address_id not in addresses:
        raise HTTPException(404, f"unknown address_id {address_id}")
    addr = addresses[address_id]
    rules = load_rules()
    by_id = {r["team_rule_id"]: r for r in rules}
    lu = lookup_address(addr, rules, as_of)
    traces = []
    for row in lu.get("rules") or []:
        src = by_id.get(row["team_rule_id"], {})
        traces.append(
            {
                "team_rule_id": row["team_rule_id"],
                "result": row["result"],
                "explanation": row.get("explanation"),
                "source_doc_id": src.get("source_doc_id"),
                "source_retrieved_at": row.get("source_retrieved_at"),
                "extraction_method": src.get("extraction_method", "extract_rules"),
                "confidence": row.get("confidence"),
                "conflict_flag": row.get("conflict_flag"),
            }
        )
    return {
        "address_id": address_id,
        "as_of": as_of,
        "jurisdiction_stack": lu.get("jurisdiction_stack"),
        "legal_city": lu.get("legal_city"),
        "disclaimer": "Not legal advice.",
        "traces": traces,
        "failed_or_not_applied": lu.get("failed_or_not_applied"),
    }


@app.get("/pipeline", response_class=HTMLResponse)
def pipeline_page() -> str:
    return pipeline_page_html()


@app.get("/audit/{address_id}", response_class=HTMLResponse)
def audit_page(address_id: str, as_of: str = Query("2026-10-01")) -> str:
    """Dedicated audit view (same data as /api/audit)."""
    data = api_audit(address_id, as_of)
    body = json.dumps(data, indent=2)
    return f"""<!doctype html>
<html lang="en"><head><title>Audit {address_id}</title>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml"/>
<link rel="stylesheet" href="/static/css/app.css"/>
</head>
<body data-theme="light"><div class="shell"><nav class="nav">{_LOGO}<a href="/" class="btn-icon" style="text-decoration:none;margin-left:auto">← Home</a></nav>
<h1>Audit · {address_id}</h1>
<p class="disclaimer-banner"><strong>Not legal advice</strong></p>
<pre class="json-dump">{body}</pre></div></body></html>"""


@app.get("/api/pipeline")
def api_pipeline() -> dict:
    log_path = _OUT / "audit" / "extraction_log.jsonl"
    lines = []
    if log_path.exists():
        for raw in log_path.read_text(encoding="utf-8").splitlines()[-40:]:
            try:
                lines.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    rules = load_rules()
    methods = {}
    for r in rules:
        m = r.get("extraction_method") or "canonical"
        methods[m] = methods.get(m, 0) + 1
    return {
        "rules_total": len(rules),
        "by_extraction_method": methods,
        "recent_audit_lines": lines,
        "disclaimer": "Not legal advice.",
    }


@app.get("/api/compare")
def api_compare(
    address_id: str = Query(...),
    before: str = Query("2025-12-31"),
    after: str = Query("2026-01-02"),
) -> dict:
    addresses = {a["address_id"]: a for a in load_addresses()}
    if address_id not in addresses:
        raise HTTPException(404, f"unknown address_id {address_id}")
    rules = load_rules()
    addr = addresses[address_id]
    return {
        "before": lookup_address(addr, rules, before),
        "after": lookup_address(addr, rules, after),
        "disclaimer": "Not legal advice.",
    }


def _demo_addresses() -> list[dict]:
    all_addrs = load_addresses()
    want = [
        ("San Francisco", "CA"),
        ("Los Angeles", "CA"),
        ("Hoboken", "NJ"),
        ("Jersey City", "NJ"),
        ("Newark", "NJ"),
        ("Boston", "MA"),
        ("Cambridge", "MA"),
        ("Berkeley", "CA"),
        ("San Diego", "CA"),
    ]
    picked: list[dict] = []
    for city, state in want:
        hit = next(
            (
                a
                for a in all_addrs
                if a.get("state") == state
                and city.lower()
                in (
                    (a.get("legal_city") or "").lower(),
                    (a.get("postal_city") or "").lower(),
                )
            ),
            None,
        )
        if hit:
            picked.append(hit)
    return picked or all_addrs[:10]


@app.get("/api/demo-presets")
def api_demo_presets() -> dict:
    return {
        "cities": _demo_addresses(),
        "change_tests": [
            {"id": "T1", "label": "T1 Before (2025-12-31)", "address_id": "A0001", "as_of": "2025-12-31"},
            {"id": "T1b", "label": "T1 After (2026-01-02)", "address_id": "A0001", "as_of": "2026-01-02"},
            {"id": "T2_hob", "label": "T2 Hoboken", "address_id": "A0002", "as_of": "2026-10-01"},
            {"id": "T2_jc", "label": "T2 Jersey City", "address_id": "A0003", "as_of": "2026-10-01"},
            {"id": "T3", "label": "T3 FAIR Act in Effect", "address_id": "A0002", "as_of": "2027-07-02"},
            {"id": "T4", "label": "T4 MA Pending Bills", "address_id": "A0006", "as_of": "2026-10-01"},
            {"id": "T5", "label": "T5 MA Struck Ballot", "address_id": "A0006", "as_of": "2026-10-01"},
        ],
        "open_questions": [
            {"id": "Q1", "label": "Berkeley Dual Dates (Ch. 13.63)", "address_id": "A0005", "as_of": "2026-10-01", "rule_id": "BERK-ALG-01"},
            {"id": "Q2", "label": "NJ FAIR Preemption", "address_id": "A0002", "as_of": "2027-07-02", "rule_id": "NJ-ALG-01"},
            {"id": "Q3", "label": "LA RSO Dual Dates", "address_id": "A0001", "as_of": "2026-10-01", "rule_id": "LA-RSO-02"},
            {"id": "Q4", "label": "CA Screening Fee Gap", "address_id": "A0005", "as_of": "2026-10-01", "rule_id": "BERK-SCR-01"},
        ],
        "disclaimer": "Not legal advice.",
    }


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return home_page(len(load_addresses()), len(load_rules()))
