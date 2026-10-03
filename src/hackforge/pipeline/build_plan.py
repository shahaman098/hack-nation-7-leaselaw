from __future__ import annotations

import copy
import json
import re
from typing import Any

import jsonschema

from hackforge.models import BuildPlan, CandidateIdea, CompetitionBrief, FeasibilityReport
from hackforge.paths import SCHEMAS_DIR
from hackforge.providers import LLMProvider
from hackforge.utils import load_prompt, read_json

_GENERATED_FIELDS = ("summary", "architecture", "tasks", "demo_script", "cut_scope", "submission_checklist")


def create_build_plan(
    provider: LLMProvider,
    brief: CompetitionBrief,
    candidate: CandidateIdea,
    feasibility: FeasibilityReport,
    red_team: dict[str, Any],
) -> BuildPlan:
    if feasibility.candidate_id != candidate.id:
        raise ValueError("Build plan requires the selected candidate's existing feasibility report")
    template, _ = load_prompt("build-plan")
    window = (brief.build_window or "").strip() or None
    if window and re.match(r"(?i)^(unknown\b|not (specified|provided|stated)\b|unspecified\b|tbd\b|n/?a$|no (explicit )?(timebox|build window)\b)", window):
        window = None
    artifact_schema = read_json(SCHEMAS_DIR / "build-plan.json")
    generation_schema: dict[str, Any] = {
        "type": "object", "additionalProperties": False,
        "required": list(_GENERATED_FIELDS),
        "properties": {key: copy.deepcopy(artifact_schema["properties"][key]) for key in _GENERATED_FIELDS},
    }
    if window is None:
        generation_schema["properties"]["tasks"]["items"]["properties"]["time_slot"] = {"type": "null"}
    payload = {
        "brief": brief.model_dump(), "build_window": window,
        "candidate": candidate.model_dump(), "existing_feasibility": feasibility.model_dump(),
        "red_team_conditions": red_team,
    }
    # One bounded call, through the existing provider instance and its budget.
    raw = provider.complete_json(template, json.dumps(payload), schema=generation_schema, retries=0)
    jsonschema.validate(raw, generation_schema)
    plan = BuildPlan.model_validate({
        **raw, "candidate_id": candidate.id,
        "scheduling_status": "scheduled" if window else "unscheduled", "build_window": window,
        "feasibility_report": feasibility.model_dump(),
    })
    jsonschema.validate(plan.model_dump(), artifact_schema)
    return plan


def build_plan_markdown(plan: BuildPlan) -> str:
    report = plan.feasibility_report
    lines = [f"# Build plan: {plan.candidate_id}", "", plan.summary, "",
             f"Scheduling: **{plan.scheduling_status}**", f"Build window: {plan.build_window or 'not supplied'}"]
    if plan.scheduling_status == "unscheduled":
        lines.append("No timebox supplied: dependency order only; no hour/day allocations invented.")
    lines.extend(["", "## Existing feasibility (reused, not reassessed)",
                  f"- Delivery risk: {report.delivery_risk}", f"- Non-fakeable core: {report.non_fakeable_core}",
                  f"- Minimum loop: {report.minimum_demonstrable_loop}",
                  f"- Critical dependencies: {', '.join(report.critical_dependencies)}",
                  f"- Permitted mocks: {', '.join(report.fakeable_parts)}", f"- Notes: {report.notes}",
                  "", "## Architecture", *[f"- {item}" for item in plan.architecture], "", "## Tasks"])
    for task in plan.tasks:
        lines.extend([f"### {task.id}: {task.title}", f"- Owner role: {task.owner_role}",
                      f"- Depends on: {', '.join(task.depends_on) or 'none'}",
                      f"- Slot: {task.time_slot or 'unscheduled'}", f"- Deliverable: {task.deliverable}",
                      f"- Acceptance test: {task.acceptance_test}", ""])
    lines.extend(["## Demo script", *[f"{index}. {step}" for index, step in enumerate(plan.demo_script, 1)],
                  "", "## Cut scope", *[f"- {item}" for item in plan.cut_scope], "",
                  "## Submission checklist", *[f"- {item}" for item in plan.submission_checklist]])
    return "\n".join(lines)
