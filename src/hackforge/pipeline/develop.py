"""Bounded autonomous development of the selected build plan.

Each build-plan task becomes a small number of schema-validated calls that write
real files under the run's product/ directory. File writes are confined to the
product root; acceptance checks and the GUI boot smoke run only when the
operator explicitly passes execute_checks.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import jsonschema

from hackforge.models import (
    BuildPlan,
    CompetitionBrief,
    DevelopmentReport,
    DevFile,
    DevScaffold,
    DevTaskOutput,
    GuiSmoke,
)
from hackforge.paths import SCHEMAS_DIR
from hackforge.providers import LLMProvider
from hackforge.utils import load_prompt, read_json

_MAX_REPAIRS = 1
_CHECK_TIMEOUT_SECONDS = 180
_SMOKE_TIMEOUT_SECONDS = 90

_FILE_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["path", "content"],
        "properties": {"path": {"type": "string", "minLength": 1}, "content": {"type": "string"}},
    },
}

SCAFFOLD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["scaffold", "files"],
    "properties": {
        "scaffold": {
            "type": "object",
            "additionalProperties": False,
            "required": ["stack", "entry_point"],
            "properties": {
                "stack": {"type": "string", "minLength": 1},
                "entry_point": {"type": "string", "minLength": 1},
                "run_command": {"type": ["string", "null"]},
                "url": {"type": ["string", "null"]},
                "notes": {"type": "string"},
            },
        },
        "files": _FILE_SCHEMA,
    },
}

TASK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["files"],
    "properties": {
        "files": _FILE_SCHEMA,
        "check_command": {"type": ["string", "null"]},
        "notes": {"type": "string"},
    },
}


def _safe_product_path(product_root: Path, relative: str) -> Path:
    candidate = (product_root / relative).resolve()
    root = product_root.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"Generated file escapes the product directory: {relative!r}")
    return candidate


def _write_files(product_root: Path, files: list[DevFile]) -> list[str]:
    written: list[str] = []
    for file in files:
        target = _safe_product_path(product_root, file.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            file.content if file.content.endswith("\n") else file.content + "\n", encoding="utf-8"
        )
        target.chmod(0o600)
        written.append(file.path)
    return written


def _run_check(product_root: Path, command: str) -> tuple[str, str]:
    try:
        argv = shlex.split(command)
    except ValueError:
        return "failed", "unparseable check command"
    if not argv:
        return "failed", "empty check command"
    try:
        proc = subprocess.run(
            argv,
            cwd=product_root,
            capture_output=True,
            text=True,
            timeout=_CHECK_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return "failed", f"command not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return "failed", f"check timed out after {_CHECK_TIMEOUT_SECONDS}s"
    output = ((proc.stdout or "") + (proc.stderr or ""))[-2000:]
    if proc.returncode == 0:
        return "passed", output
    return "failed", output


def _gui_smoke(product_root: Path, scaffold: DevScaffold) -> GuiSmoke:
    if not scaffold.run_command or not scaffold.url:
        return GuiSmoke(
            attempted=False, ok=False, notes="scaffold declares no run_command/url; smoke skipped"
        )
    try:
        argv = shlex.split(scaffold.run_command)
    except ValueError:
        return GuiSmoke(
            attempted=True,
            ok=False,
            command=scaffold.run_command,
            url=scaffold.url,
            notes="unparseable run command",
        )
    proc = subprocess.Popen(argv, cwd=product_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + _SMOKE_TIMEOUT_SECONDS
    http_status: int | None = None
    note = "server did not respond before the smoke timeout"
    try:
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(scaffold.url, timeout=5) as response:
                    http_status = response.status
                    note = ""
                    break
            except urllib.error.HTTPError as exc:
                http_status = exc.code
                note = "server responded with an HTTP error"
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                time.sleep(2)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    ok = http_status is not None and 200 <= http_status < 400
    return GuiSmoke(
        attempted=True,
        ok=ok,
        command=scaffold.run_command,
        url=scaffold.url,
        http_status=http_status,
        notes=note,
    )


def develop_product(
    provider: LLMProvider,
    brief: CompetitionBrief,
    plan: BuildPlan,
    product_root: Path,
    *,
    execute_checks: bool = False,
) -> DevelopmentReport:
    template, _ = load_prompt("develop")
    artifact_schema = read_json(SCHEMAS_DIR / "development-report.json")
    product_root.mkdir(parents=True, exist_ok=True)
    product_root.chmod(0o700)

    plan_payload = plan.model_dump()
    written: list[str] = []

    scaffold_payload = {
        "call": "develop scaffold call",
        "brief": brief.model_dump(),
        "plan": plan_payload,
        "product_root_name": product_root.name,
    }
    raw_scaffold = provider.complete_json(
        template, json.dumps(scaffold_payload), schema=SCAFFOLD_SCHEMA, retries=0
    )
    jsonschema.validate(raw_scaffold, SCAFFOLD_SCHEMA)
    scaffold = DevScaffold.model_validate(raw_scaffold["scaffold"])
    written.extend(_write_files(product_root, [DevFile.model_validate(f) for f in raw_scaffold["files"]]))

    records = []
    for task in plan.tasks:
        task_payload = {
            "call": "develop task call",
            "brief": brief.model_dump(),
            "plan": plan_payload,
            "task": task.model_dump(),
            "written_files": sorted(set(written)),
        }
        output = provider.complete_json(template, json.dumps(task_payload), schema=TASK_SCHEMA, retries=0)
        jsonschema.validate(output, TASK_SCHEMA)
        parsed = DevTaskOutput.model_validate(output)
        attempts = 0
        task_written = _write_files(product_root, parsed.files)
        written.extend(task_written)
        check_status = "not_run"
        if execute_checks and parsed.check_command:
            check_status, check_output = _run_check(product_root, parsed.check_command)
            if check_status == "failed" and attempts < _MAX_REPAIRS:
                attempts += 1
                repair_payload = {
                    **task_payload,
                    "previous_attempt": parsed.model_dump(),
                    "check_command": parsed.check_command,
                    "check_output": check_output,
                }
                repair = provider.complete_json(
                    template, json.dumps(repair_payload), schema=TASK_SCHEMA, retries=0
                )
                jsonschema.validate(repair, TASK_SCHEMA)
                parsed = DevTaskOutput.model_validate(repair)
                task_written = _write_files(product_root, parsed.files)
                written.extend(task_written)
                if parsed.check_command:
                    check_status, _ = _run_check(product_root, parsed.check_command)
        records.append(
            {
                "task_id": task.id,
                "title": task.title,
                "status": "implemented" if check_status != "failed" else "failed",
                "files_written": task_written,
                "check_command": parsed.check_command,
                "check_status": check_status,
                "repair_attempts": attempts,
                "notes": parsed.notes,
            }
        )

    smoke = _gui_smoke(product_root, scaffold) if execute_checks else None
    report = DevelopmentReport.model_validate(
        {
            "candidate_id": plan.candidate_id,
            "product_root": str(product_root),
            "checks_executed": execute_checks,
            "scaffold": scaffold.model_dump(),
            "tasks": records,
            "gui_smoke": smoke.model_dump() if smoke else None,
            "notes": "acceptance checks and GUI smoke executed locally"
            if execute_checks
            else "files written only; pass --execute to run acceptance checks and the GUI smoke",
        }
    )
    jsonschema.validate(report.model_dump(), artifact_schema)
    return report
