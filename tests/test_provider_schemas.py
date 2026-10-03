"""Codex wire-schema normalization.

`_codex_strict_schema` rewrites a JSON Schema for Codex's strict response_format.
It had two failure modes that only appear against the live API, so every shipped
schema is exercised here rather than one hand-picked example.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from hackforge.paths import SCHEMAS_DIR
from hackforge.providers import _CODEX_UNSUPPORTED_KEYWORDS, _codex_strict_schema

SCHEMA_FILES = sorted(SCHEMAS_DIR.glob("*.json"))


def _keywords_outside_properties(node: Any, path: str = "", *, under_properties: bool = False) -> list[str]:
    """Find unsupported keywords in schema positions.

    Keys inside a `properties` object are field names, not annotations, so a
    field legitimately called "title" is not a violation.
    """
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if not under_properties and key in _CODEX_UNSUPPORTED_KEYWORDS:
                found.append(f"{path}.{key}")
            found.extend(
                _keywords_outside_properties(
                    value, f"{path}.{key}", under_properties=(key == "properties")
                )
            )
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(
                _keywords_outside_properties(value, f"{path}[{index}]", under_properties=under_properties)
            )
    return found


def _property_names(node: Any, out: set[str] | None = None) -> set[str]:
    """Collect every field name declared anywhere in a schema."""
    if out is None:
        out = set()
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            out.update(props)
        for value in node.values():
            _property_names(value, out)
    elif isinstance(node, list):
        for value in node:
            _property_names(value, out)
    return out


@pytest.mark.parametrize("schema_path", SCHEMA_FILES, ids=lambda p: p.name)
def test_shipped_schema_normalizes_for_codex(schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    before = copy.deepcopy(schema)

    wire = _codex_strict_schema(schema)

    # Codex answers HTTP 400 invalid_json_schema for these, killing the run.
    assert not _keywords_outside_properties(wire), (
        f"{schema_path.name} still carries keywords Codex rejects"
    )

    # Dropping a field name that collides with a keyword silently starves local
    # validation of a field Codex was never asked to produce. The rewrite may
    # legitimately *add* names (free-form maps become [{key,value}] arrays), so
    # the invariant is that no original field disappears.
    lost = _property_names(schema) - _property_names(wire)
    assert not lost, f"{schema_path.name} lost field names during normalization: {sorted(lost)}"

    # The caller validates the response against the original afterwards.
    assert schema == before, f"{schema_path.name} was mutated in place"


def test_field_named_like_a_keyword_survives() -> None:
    """`title` is both a schema annotation and a real build-plan task field."""
    schema = {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "object",
                "properties": {"title": {"type": "string", "minLength": 1}, "id": {"type": "string"}},
                "required": ["title", "id"],
                "additionalProperties": False,
            }
        },
        "required": ["tasks"],
        "additionalProperties": False,
        "title": "Example",
    }

    wire = _codex_strict_schema(schema)

    task_props = wire["properties"]["tasks"]["properties"]
    assert set(task_props) == {"title", "id"}
    assert set(wire["properties"]["tasks"]["required"]) == {"title", "id"}
    assert "title" not in wire, "the annotation keyword should still be stripped"


def test_build_plan_tasks_keep_every_required_field() -> None:
    """End-to-end shape of the schema that failed live with invalid_json_schema."""
    artifact = json.loads((SCHEMAS_DIR / "build-plan.json").read_text(encoding="utf-8"))
    generation: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": list(artifact["properties"]),
        "properties": {key: copy.deepcopy(value) for key, value in artifact["properties"].items()},
    }

    wire = _codex_strict_schema(generation)

    task_items = wire["properties"]["tasks"]["items"]
    assert set(task_items["required"]) == set(task_items["properties"])
    assert "title" in task_items["properties"]
    assert "uniqueItems" not in task_items["properties"]["depends_on"]

    # Strict mode requires every property to be required, or Codex rejects it.
    assert wire["required"] == list(wire["properties"])


def test_unsupported_keywords_are_declared() -> None:
    """Guard the list against accidental narrowing; each one broke a live run or would."""
    assert {"title", "uniqueItems", "allOf", "if", "then"} <= _CODEX_UNSUPPORTED_KEYWORDS
