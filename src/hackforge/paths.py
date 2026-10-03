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
_LOCAL_STATE_ROOT = (
    _USER_HOME
    if os.getenv("HACKFORGE_HOME")
    else (_SOURCE_ROOT if RESOURCE_ROOT == _SOURCE_ROOT else _USER_HOME)
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
    "build-plan": "v1",
    "develop": "v1",
    "winner-patterns": "v1",
}

# Broad mechanism-discovery lanes. They are intentionally format-neutral: a
# competition may produce software, hardware, science, analysis, a pitch, a
# service/process design, or another allowed artifact.
IDEATION_LANES = [
    {
        "id": "systems",
        "label": "Systems, reliability, and constrained operations",
        "disciplines": [
            "Operations research",
            "Control theory",
            "Reliability engineering",
        ],
    },
    {
        "id": "human_context",
        "label": "Human factors, accessibility, behavior, and field context",
        "disciplines": [
            "Human factors",
            "Behavioral science",
            "Accessibility and inclusive design",
        ],
    },
    {
        "id": "physical_science",
        "label": "Physical systems, sensing, experimentation, and scientific mechanisms",
        "disciplines": [
            "Experimental design",
            "Sensing and instrumentation",
            "Materials / physical systems",
        ],
    },
    {
        "id": "markets_incentives",
        "label": "Markets, incentives, finance, and resource coordination",
        "disciplines": [
            "Mechanism design",
            "Market design",
            "Finance and risk analysis",
        ],
    },
    {
        "id": "information_verification",
        "label": "Information, evidence, verification, and decision quality",
        "disciplines": [
            "Information theory",
            "Scientific reproducibility",
            "Software / formal verification",
        ],
    },
    {
        "id": "creative_strategy",
        "label": "Creative strategy, communication, service design, and adoption",
        "disciplines": [
            "Service design",
            "Communication design",
            "Strategy and organizational design",
        ],
    },
]

# Stable identifiers retained for fixture/API compatibility. These are review
# lenses only: blind-judge prompts forbid them from inventing criteria or gates.
JUDGE_ROLES = [
    "technical",
    "product",
    "sponsor",
    "domain",
    "demo-risk",
    "contrarian",
]

# Kept as a public constant for compatibility. Applicability is determined by
# evaluation.gates at runtime; absent competition requirements become not_applicable.
HARD_GATES = [
    "evidence_backed",
    "required_technology_fit",
    "requirement_compliance",
    "data_viability",
    "delivery_feasible",
    "demo_fit",
    "specific_track_fit",
    "collision_risk_acceptable",
    "independent_feasibility",
]
