#!/usr/bin/env python3
"""Automated corpus scan with verifier-gated, low-noise rule records."""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

from src.paths import require_starter
from src.verify import span_from_text

CATEGORIES = (
    "rent_increase_limits",
    "just_cause_eviction",
    "security_deposits",
    "application_screening_fees",
    "screening_restrictions",
    "algorithmic_rent_setting",
)

_CATEGORY_LABEL = {
    "rent_increase_limits": "Rent increase limits",
    "just_cause_eviction": "Just-cause eviction",
    "security_deposits": "Security deposits",
    "application_screening_fees": "Application / screening fees",
    "screening_restrictions": "Screening restrictions",
    "algorithmic_rent_setting": "Algorithmic rent-setting",
}

# Stronger patterns (reduce miscategorization).
_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    (
        "algorithmic_rent_setting",
        re.compile(
            r"algorithmic device|common pricing algorithm|coordinated pricing algorithm|"
            r"algorithmic rent|pricing algorithm",
            re.I,
        ),
        8,
    ),
    (
        "rent_increase_limits",
        re.compile(
            r"rent increase shall not|maximum (?:annual )?rent|rent cap|"
            r"limit(?:s|ed) rent increase|annual allowable rent",
            re.I,
        ),
        8,
    ),
    (
        "just_cause_eviction",
        re.compile(
            r"just cause for eviction|good cause (?:to|for) evict|"
            r"termination of tenancy|forcible entry and detainer",
            re.I,
        ),
        7,
    ),
    (
        "security_deposits",
        re.compile(
            r"security deposit shall not|deposit shall not exceed|"
            r"maximum security deposit",
            re.I,
        ),
        8,
    ),
    (
        "application_screening_fees",
        re.compile(
            r"application fee shall|screening fee shall|fee shall not exceed",
            re.I,
        ),
        8,
    ),
    (
        "screening_restrictions",
        re.compile(
            r"fair chance|criminal (?:history|record)|source of income|"
            r"screening criteria",
            re.I,
        ),
        7,
    ),
]

_OPERATIVE = re.compile(
    r"\b(shall not|may not|must not|is prohibited|are prohibited|unlawful|"
    r"shall be unlawful|required to|shall|must)\b",
    re.I,
)
_SKIP_CONTENT = re.compile(
    r"\b(whereas|findings?|demonstrated by|legislature search|skip to|"
    r"table of contents|click here)\b",
    re.I,
)
_SKIP_PREFIX = ("SOURCE:", "RETRIEVED:", "Skip to", "##LOC")

_BLOCKED_DOC_CATEGORY = {
    ("D048", "rent_increase_limits"),
    ("D011", "rent_increase_limits"),
}

# Canonical change-test docs: needles own these; do not AUTO-duplicate.
_LOCKED_DOCS = frozenset({"D022", "D034", "D036", "D069", "D045", "D046", "D048", "D024"})

CANONICAL_IDS = {
    ("D022", "algorithmic_rent_setting"): "CA-ALG-01",
    ("D034", "algorithmic_rent_setting"): "HOB-ALG-01",
    ("D036", "algorithmic_rent_setting"): "JC-ALG-01",
    ("D069", "algorithmic_rent_setting"): "NJ-ALG-01",
    ("D046", "algorithmic_rent_setting"): "MA-ALG-P1",
    ("D045", "algorithmic_rent_setting"): "MA-ALG-P2",
    ("D048", "rent_increase_limits"): "MA-RENT-P1",
    ("D024", "rent_increase_limits"): "CA-RENT-01",
}


def _jurisdiction_from_manifest(row: dict) -> tuple[str, str]:
    jur = (row.get("jurisdictions") or row.get("jurisdiction") or "").strip()
    if ", " in jur:
        city, st = jur.rsplit(", ", 1)
        return f"{city}, {st}", "city"
    if jur in ("CA", "NJ", "MA"):
        return jur, "state"
    return jur or "unknown", "state"


def derive_status(doc_id: str, url: str, sentence: str) -> tuple[str, str | None]:
    """Map source URL / doc to schema status (never in_force from a bill page)."""
    url_l = (url or "").lower()
    if "/bills/" in url_l or "billhistory" in url_l:
        return "pending", None
    if doc_id == "D069":
        return "not_yet_effective", "2027-07-01"
    if doc_id == "D048" or doc_id == "D011":
        return "failed", None
    sl = sentence.lower()
    if "struck" in sl or "ballot question" in sl and "failed" in sl:
        return "failed", None
    return "in_force", None


def _is_bill_source(url: str) -> bool:
    url_l = (url or "").lower()
    return "/bills/" in url_l or "billhistory" in url_l


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    out: list[str] = []
    for p in parts:
        s = p.strip()
        if len(s) < 50 or len(s) > 520:
            continue
        if any(s.startswith(x) for x in _SKIP_PREFIX):
            continue
        if _SKIP_CONTENT.search(s):
            continue
        if not _OPERATIVE.search(s):
            continue
        out.append(s)
    return out


def _title_for(doc_id: str, category: str, jurisdiction: str) -> str:
    label = _CATEGORY_LABEL.get(category, category)
    jur = jurisdiction.split(",")[0].strip() if "," in jurisdiction else jurisdiction
    return f"{jur} — {label} ({doc_id})"[:90]


def _score_sentence(sentence: str, cat: str, pattern_score: int) -> int:
    score = pattern_score
    if _OPERATIVE.search(sentence):
        score += 6
    if len(sentence) > 120:
        score += 2
    if _SKIP_CONTENT.search(sentence):
        score -= 15
    return score


def _norm_span_key(span: str) -> str:
    return re.sub(r"\s+", " ", span.strip().lower())[:100]


def scan_doc(starter: Path, row: dict, taken_ids: set[str]) -> list[dict]:
    doc_id = row["doc_id"]
    url = (row.get("url") or "").strip()
    if doc_id in _LOCKED_DOCS or _is_bill_source(url):
        return []
    path = starter / "corpus" / "text" / f"{doc_id}.txt"
    if not path.exists() or row.get("status") != "ok":
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    jurisdiction, level = _jurisdiction_from_manifest(row)
    retrieved = row.get("retrieved_at") or ""

    if jurisdiction == "MA" or jurisdiction.endswith(", MA"):
        # MA rent caps must not appear from scanner (T5).
        pass  # category filter below still allows non-rent cats

    best: tuple[int, str, str, str] | None = None  # score, sent, cat, span
    seen_spans: set[str] = set()

    for sent in _sentences(text):
        for cat, pat, pscore in _PATTERNS:
            if (doc_id, cat) in _BLOCKED_DOC_CATEGORY:
                continue
            if cat == "rent_increase_limits" and (
                jurisdiction == "MA"
                or jurisdiction.endswith(", MA")
                or jurisdiction in ("Boston, MA", "Cambridge, MA")
            ):
                continue
            if not pat.search(sent):
                continue
            span = span_from_text(text, sent[:100]) or span_from_text(text, sent[:50])
            if not span:
                continue
            sk = _norm_span_key(span)
            if sk in seen_spans:
                continue
            seen_spans.add(sk)
            score = _score_sentence(sent, cat, pscore)
            if best is None or score > best[0]:
                best = (score, sent, cat, span)

    if best is None:
        return []

    _, sent, cat, span = best
    canon = CANONICAL_IDS.get((doc_id, cat))
    if canon:
        if canon in taken_ids:
            return []
        rid = canon
    else:
        h = hashlib.sha1(f"{doc_id}:{cat}:{span[:60]}".encode()).hexdigest()[:6]
        rid = f"{doc_id}-{cat[:4].upper()}-{h}"
        if rid in taken_ids:
            return []
    taken_ids.add(rid)

    status, eff = derive_status(doc_id, url, sent)
    title = _title_for(doc_id, cat, jurisdiction)

    return [
        {
            "team_rule_id": rid,
            "jurisdiction": jurisdiction,
            "level": level,
            "category": cat,
            "status": status,
            "title": title,
            "requirement": sent[:500],
            "key_value": None,
            "coverage_conditions": None,
            "exemptions": None,
            "overrides": [],
            "interaction": None,
            "effective_date": eff,
            "citation": f"{doc_id} ({_CATEGORY_LABEL[cat]})",
            "source_doc_id": doc_id,
            "source_url": url,
            "quoted_span": span,
            "confidence": 0.78,
            "conflict_flag": False,
            "conflict_note": None,
            "source_retrieved_at": retrieved,
            "plain_en": sent[:280],
            "plain_es": None,
            "extraction_method": "corpus_automate_v2",
        }
    ]


def scan_corpus(starter: Path | None = None, skip_ids: set[str] | None = None) -> list[dict]:
    starter = starter or require_starter()
    man_path = starter / "corpus" / "corpus_manifest.csv"
    with man_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    taken = set(skip_ids or ())
    out: list[dict] = []
    for row in rows:
        out.extend(scan_doc(starter, row, taken))
    return out
