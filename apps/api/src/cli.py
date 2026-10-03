#!/usr/bin/env python3
"""AppealPath Diff — terminal demo (no UI)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fastapi import HTTPException

from main import SAMPLE_NOTICES, analyze_notice, AnalyzeRequest


def _load_notice(args: argparse.Namespace) -> str:
    if args.sample:
        for row in SAMPLE_NOTICES:
            if row["id"] == args.sample:
                return row["text"]
        raise SystemExit(f"Unknown sample id: {args.sample}")
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.text:
        return args.text
    raise SystemExit("Provide --sample, --file, or --text")


def _print_checks(checks: list, indent: str = "  ") -> None:
    for c in checks:
        if isinstance(c, dict):
            status = c["status"]
            name = c["name"]
            expected = c.get("expected")
            observed = c.get("observed")
        else:
            status = c.status
            name = c.name
            expected = c.expected
            observed = c.observed
        mark = "✓" if status == "pass" else "✗" if status == "fail" else "–"
        extra = ""
        if expected is not None or observed is not None:
            extra = f" (expected {expected}, observed {observed})"
        print(f"{indent}{mark} {name}{extra}")


def _print_human(result) -> None:
    data = result.model_dump()
    print(f"Case: {data['case_number']} — {data['claimant_name']}")
    print(f"Decision date: {data['decision_date']}")
    print(f"Governing rules: {data['governing_rule_version']}")
    print("Verification:")
    _print_checks(data["checks"])
    if data.get("loop_iterations"):
        print("\nAgent Loop Execution (Evaluator-Optimizer):")
        for step in data["loop_iterations"]:
            mark = "✓" if step["result"] == "pass" else "✗" if step["result"] == "fail" else "↻"
            print(f"  [{step['iteration']}] {mark} {step['stage']} ({step['target']}): {step['feedback']}")
    print(f"\nAppeal deadline (governing): {data['appeal_filing_deadline']} ({data['days_remaining_or_overdue']}d vs today)")
    if data["wrongful_application_detected"]:
        print(f"\n⚠ {data['wrongful_application_summary']}\n")
    print("Clause diff:")
    for c in data["clause_diffs"]:
        flag = " [CHANGED]" if c["has_changed"] else ""
        print(f"  - {c['clause_id']}{flag}: {c['impact_note']}")
    print("\nEvidence checklist:")
    for item in data["required_evidence_checklist"]:
        mark = "!" if item["is_missing_or_vulnerable"] else "✓"
        print(f"  {mark} {item['requirement']}")
        print(f"      → {item['actionable_remedy']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AppealPath Diff CLI")
    parser.add_argument("--sample", help="Sample notice id (see --list-samples)")
    parser.add_argument("--file", type=Path, help="Path to notice text file")
    parser.add_argument("--text", help="Inline notice text")
    parser.add_argument("--json", action="store_true", help="Emit full JSON")
    parser.add_argument("--list-samples", action="store_true", help="List sample ids")
    args = parser.parse_args(argv)

    if args.list_samples:
        for row in SAMPLE_NOTICES:
            print(f"{row['id']}\t{row['title']}")
        return 0

    notice = _load_notice(args)
    try:
        result = analyze_notice(AnalyzeRequest(notice_text=notice))
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
        if args.json:
            print(json.dumps(detail, indent=2))
        else:
            print("UNVERIFIED — no analysis produced")
            checks = detail.get("checks", [])
            if checks:
                print("Verification:")
                _print_checks(checks)
        return 2

    if args.json:
        print(json.dumps(result.model_dump(), indent=2))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
