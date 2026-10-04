#!/usr/bin/env python3
"""LLM-assisted extraction with offline cache; strict corpus scan when no cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.corpus_automate import scan_corpus  # noqa: E402
from src.extract_rules import extract_all_needles_only  # noqa: E402
from src.paths import APP_ROOT, require_starter  # noqa: E402
from src.verify import is_literal_span, span_from_text  # noqa: E402

PROMPT_VERSION = "v2"
DEFAULT_MODEL = os.environ.get("LEASELAW_MODEL", "claude-sonnet-5-5")
CACHE_DIR = APP_ROOT / "out" / "llm_cache"
AUDIT_LOG = APP_ROOT / "out" / "audit" / "extraction_log.jsonl"

CANONICAL_IDS = frozenset(
    {
        "CA-ALG-01",
        "HOB-ALG-01",
        "JC-ALG-01",
        "NJ-ALG-01",
        "MA-ALG-P1",
        "MA-ALG-P2",
        "MA-RENT-P1",
    }
)


def _merge_rules(primary: list[dict], secondary: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in primary + secondary:
        rid = r["team_rule_id"]
        if rid in seen:
            continue
        seen.add(rid)
        out.append(r)
    return out


def _load_cache_rules() -> list[dict]:
    merged: list[dict] = []
    if not CACHE_DIR.exists():
        return merged
    for path in sorted(CACHE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            merged.extend(data)
    return [r for r in merged if not r.get("team_rule_id", "").startswith("AUTO-")]


def _append_audit(line: dict) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


def _chunk_text(text: str, max_chars: int = 12000) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    parts = re.split(r"\n(?=[A-Z0-9][A-Z0-9 .]{8,}\n)", text)
    buf = ""
    for p in parts:
        if len(buf) + len(p) > max_chars and buf:
            chunks.append(buf)
            buf = p
        else:
            buf = (buf + "\n" + p) if buf else p
    if buf:
        chunks.append(buf)
    return chunks or [text[:max_chars]]


def _verify_llm_record(record: dict, text: str, manifest_row: dict) -> dict | None:
    span = record.get("quoted_span") or ""
    if not is_literal_span(text, span) and span_from_text(text, span[:80]) is None:
        return None
    if span_from_text(text, span[:40]):
        record["quoted_span"] = span_from_text(text, span[:80]) or span
    record["source_doc_id"] = manifest_row["doc_id"]
    record["source_url"] = manifest_row.get("url") or record.get("source_url")
    record["source_retrieved_at"] = manifest_row.get("retrieved_at")
    record["extraction_method"] = "llm_v2"
    rid = record.get("team_rule_id") or ""
    if rid.startswith("AUTO-") or rid in CANONICAL_IDS:
        return None
    return record


def _run_llm_extraction(starter: Path, api_key: str) -> list[dict]:
    import anthropic  # type: ignore

    import csv

    client = anthropic.Anthropic(api_key=api_key)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    kept: list[dict] = []
    man = list(csv.DictReader((starter / "corpus" / "corpus_manifest.csv").open()))
    tool_schema = {
        "name": "emit_rules",
        "description": "Emit zero or more housing rule records from this corpus chunk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rules": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "team_rule_id": {"type": "string"},
                            "jurisdiction": {"type": "string"},
                            "level": {"type": "string", "enum": ["state", "city"]},
                            "category": {
                                "type": "string",
                                "enum": list(
                                    (
                                        "rent_increase_limits",
                                        "just_cause_eviction",
                                        "security_deposits",
                                        "application_screening_fees",
                                        "screening_restrictions",
                                        "algorithmic_rent_setting",
                                    )
                                ),
                            },
                            "status": {
                                "type": "string",
                                "enum": [
                                    "in_force",
                                    "not_yet_effective",
                                    "pending",
                                    "failed",
                                ],
                            },
                            "title": {"type": "string"},
                            "requirement": {"type": "string"},
                            "effective_date": {"type": ["string", "null"]},
                            "citation": {"type": "string"},
                            "quoted_span": {"type": "string"},
                            "plain_en": {"type": "string"},
                            "plain_es": {"type": "string"},
                        },
                        "required": [
                            "jurisdiction",
                            "level",
                            "category",
                            "status",
                            "title",
                            "requirement",
                            "citation",
                            "quoted_span",
                        ],
                    },
                }
            },
            "required": ["rules"],
        },
    }

    for row in man:
        if row.get("status") != "ok":
            continue
        doc_id = row["doc_id"]
        if doc_id in {"D022", "D034", "D036", "D069", "D045", "D046", "D048", "D024"}:
            continue
        path = starter / "corpus" / "text" / f"{doc_id}.txt"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        doc_rules: list[dict] = []
        for chunk in _chunk_text(text):
            prompt = (
                f"Extract enforceable housing rules from this public law text ({doc_id}). "
                "Copy quoted_span VERBATIM from the text. Bills → status pending. "
                "Do not invent rules. Max 3 rules per chunk. team_rule_id format: "
                f"LLM-{doc_id}-{{category}}-{{nn}}."
            )
            msg = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=4096,
                tools=[tool_schema],
                tool_choice={"type": "tool", "name": "emit_rules"},
                messages=[
                    {"role": "user", "content": prompt + "\n\n---\n\n" + chunk[:14000]}
                ],
            )
            for block in msg.content:
                if block.type != "tool_use":
                    continue
                for rec in block.input.get("rules") or []:
                    verified = _verify_llm_record(rec, text, row)
                    if verified:
                        doc_rules.append(verified)
        cache_path = CACHE_DIR / f"{doc_id}.json"
        cache_path.write_text(json.dumps(doc_rules, indent=2) + "\n", encoding="utf-8")
        kept.extend(doc_rules)
        _append_audit(
            {
                "mode": "llm_doc",
                "doc_id": doc_id,
                "kept": len(doc_rules),
                "model": DEFAULT_MODEL,
                "prompt_version": PROMPT_VERSION,
            }
        )
    return kept


def build_rules(offline: bool = True) -> list[dict]:
    starter = require_starter()
    canonical = extract_all_needles_only()
    canon_ids = {r["team_rule_id"] for r in canonical}

    llm_rules: list[dict] = []
    automated: list[dict] = []

    if offline:
        llm_rules = _load_cache_rules()
        if llm_rules:
            _append_audit(
                {
                    "mode": "offline_cache",
                    "rules": len(llm_rules),
                    "prompt_version": PROMPT_VERSION,
                }
            )
        else:
            automated = scan_corpus(starter, skip_ids=canon_ids)
            _append_audit(
                {
                    "mode": "corpus_automate_v2",
                    "proposed": len(automated),
                    "starter": str(starter),
                    "prompt_version": PROMPT_VERSION,
                }
            )
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            _append_audit({"mode": "llm_skipped", "reason": "no ANTHROPIC_API_KEY"})
            automated = scan_corpus(starter, skip_ids=canon_ids)
        else:
            llm_rules = _run_llm_extraction(starter, api_key)
            automated = []  # LLM replaces AUTO-*

    if llm_rules:
        automated = [r for r in automated if not r.get("team_rule_id", "").startswith("AUTO-")]

    return _merge_rules(canonical, _merge_rules(llm_rules, automated))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", default=True)
    parser.add_argument("--live", action="store_true", help="Call Anthropic API (needs key)")
    args = parser.parse_args()
    offline = not args.live
    rules = build_rules(offline=offline)
    out = APP_ROOT / "out" / "rules.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rules, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rules)} rules → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
