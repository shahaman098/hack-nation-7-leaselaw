from __future__ import annotations

import os
import sysconfig
from pathlib import Path

# Prefer repository resources for editable development and wheel data for installed releases.
_SOURCE_ROOT = Path(__file__).resolve().parents[2]
_INSTALLED_RESOURCE_ROOT = Path(sysconfig.get_path("data")) / "share" / "hackforge"
RESOURCE_ROOT = _SOURCE_ROOT if (_SOURCE_ROOT / "prompts").exists() else _INSTALLED_RESOURCE_ROOT
REPO_ROOT = RESOURCE_ROOT
PROMPTS_DIR = RESOURCE_ROOT / "prompts"
SCHEMAS_DIR = RESOURCE_ROOT / "schemas"
CORPORA_DIR = RESOURCE_ROOT / "corpora"
_USER_HOME = Path(os.getenv("HACKFORGE_HOME") or (Path.home() / ".hackforge"))
# Editable checkouts keep state beside the repo by default, which makes a quick
# personal setup frictionless. An explicit HACKFORGE_HOME always wins, including
# in a source checkout, so operators can keep every writable artifact elsewhere.
_LOCAL_STATE_ROOT = (
    _USER_HOME if os.getenv("HACKFORGE_HOME") else (_SOURCE_ROOT if RESOURCE_ROOT == _SOURCE_ROOT else _USER_HOME)
)
CORPUS_CACHE_DIR = Path(
    os.getenv("HACKFORGE_CORPUS_CACHE") or (_LOCAL_STATE_ROOT / "corpora" / "cache")
)
INDEX_DIR = Path(
    os.getenv("HACKFORGE_INDEX_DIR") or (_LOCAL_STATE_ROOT / "corpora" / "indexes" / "default")
)
HACKREP_DIR = Path(os.getenv("HACKFORGE_HACKREP_DIR") or (_LOCAL_STATE_ROOT / "corpora" / "hackrep"))
RUNS_DIR = Path(os.getenv("HACKFORGE_RUNS_DIR") or (_LOCAL_STATE_ROOT / "runs"))
EVALS_DIR = _LOCAL_STATE_ROOT / "evals"
FIXTURES_DIR = RESOURCE_ROOT / "fixtures"

PROMPT_VERSIONS = {
    "competition-research": "v1",
    "contrarian-ideation": "v1",
    "opportunity-discovery": "v1",
    "mechanism-mining": "v1",
    "idea-crossing": "v1",
    "reflective-mutation": "v1",
    "collision-audit": "v1",
    "feasibility": "v1",
    "blind-judge": "v1",
    "red-team": "v1",
}

IDEATION_LANES = [
    {
        "id": "institutional",
        "label": "Institutional and bureaucratic failures",
        "disciplines": [
            "Public administration",
            "Procedural fairness",
            "Administrative error prevention",
        ],
    },
    {
        "id": "systems_or",
        "label": "Optimization and systems engineering",
        "disciplines": [
            "Operations research",
            "Control theory",
            "Supply-chain engineering",
        ],
    },
    {
        "id": "edge_users",
        "label": "Safety, accessibility, and edge users",
        "disciplines": [
            "Human factors",
            "Epidemiology",
            "Reliability engineering",
        ],
    },
    {
        "id": "incentives",
        "label": "Economic incentives and market coordination",
        "disciplines": [
            "Mechanism design",
            "Insurance science",
            "Forensic accounting",
        ],
    },
]

JUDGE_ROLES = [
    "technical",
    "product",
    "sponsor",
    "domain",
    "demo-risk",
    "contrarian",
]

HARD_GATES = [
    "demonstrable_core",
    "real_computation_or_action",
    "data_accessible",
    "specific_track_fit",
    "sponsor_tech_material_or_explicitly_unnecessary",
    "core_loop_deliverable",
    "clear_60s_transformation",
    "collision_risk_acceptable",
]
