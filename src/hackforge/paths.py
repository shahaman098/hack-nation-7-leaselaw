from __future__ import annotations

from pathlib import Path

# Repository root: .../Idea Generation (parents: hackforge -> src -> root)
REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "prompts"
SCHEMAS_DIR = REPO_ROOT / "schemas"
CORPORA_DIR = REPO_ROOT / "corpora"
CORPUS_CACHE_DIR = CORPORA_DIR / "cache"
INDEX_DIR = CORPORA_DIR / "indexes" / "default"
HACKREP_DIR = CORPORA_DIR / "hackrep"
RUNS_DIR = REPO_ROOT / "runs"
EVALS_DIR = REPO_ROOT / "evals"
FIXTURES_DIR = REPO_ROOT / "fixtures"

PROMPT_VERSIONS = {
    "competition-research": "v1",
    "contrarian-ideation": "v1",
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
