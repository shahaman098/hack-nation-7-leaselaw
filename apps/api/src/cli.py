#!/usr/bin/env python3
"""AppealPath Diff — terminal demo (no UI)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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


def _print_human(result) -> None:
    data = result.model_dump()
    print(f"Case: {data['case_number']} — {data['claimant_name']}")
    print(f"Decision date: {data['decision_date']}")
    print(f"Governing rules: {data['governing_rule_version']}")
    print(f"Appeal deadline (governing): {data['appeal_filing_deadline']} ({data['days_remaining_or_overdue']}d vs today)")
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
    result = analyze_notice(AnalyzeRequest(notice_text=notice))
    if args.json:
        print(json.dumps(result.model_dump(), indent=2))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
