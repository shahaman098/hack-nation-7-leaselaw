from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from hackforge.paths import EVALS_DIR, FIXTURES_DIR, PROMPTS_DIR, REPO_ROOT
from hackforge.utils import write_text


def promptfoo_config_dir() -> Path:
    d = EVALS_DIR / "promptfoo"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_promptfoo_config() -> Path:
    """Write baseline vs ideation prompt comparison config."""
    cfg_dir = promptfoo_config_dir()
    brief = (FIXTURES_DIR / "sample-hackathon.md").read_text(encoding="utf-8")
    ideation = (PROMPTS_DIR / "contrarian-ideation" / "v1.md").read_text(encoding="utf-8")
    baseline_prompt = (
        "You are a hackathon idea generator.\n"
        "Here is the hackathon description. Give me ten winning ideas.\n\n{{brief}}"
    )
    pipeline_prompt = (
        ideation.replace("{{LANE}}", "Institutional")
        .replace("{{DISCIPLINES}}", "- Public administration")
        .replace("{{SANITIZED_BRIEF}}", "{{brief}}")
        .replace("{{BLACKLIST}}", "tutors, summarisers, navigators, wellness bots")
        .replace("{{SEED_COUNT}}", "5")
    )
    write_text(cfg_dir / "baseline.txt", baseline_prompt)
    write_text(cfg_dir / "pipeline.txt", pipeline_prompt)

    cfg = {
        "description": "HackForge baseline vs pipeline ideation (no idea-chatbot wrappers)",
        "prompts": ["baseline.txt", "pipeline.txt"],
        "providers": [
            {"id": "openai:gpt-4o", "config": {"temperature": 0.4}},
        ],
        "tests": [
            {
                "vars": {"brief": brief[:6000]},
                "assert": [
                    {"type": "not-icontains", "value": "wellness chatbot"},
                    {"type": "not-icontains", "value": "AI tutor"},
                ],
            }
        ],
    }
    path = cfg_dir / "promptfooconfig.yaml"
    import yaml

    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return path


def run_promptfoo(*, dry_run: bool = False) -> dict[str, Any]:
    cfg = ensure_promptfoo_config()
    if dry_run or not shutil.which("npx"):
        return {
            "status": "skipped",
            "reason": "npx/promptfoo unavailable or dry_run — config written only",
            "config": str(cfg),
            "hint": "brew install node && npx promptfoo@latest eval -c evals/promptfoo/promptfooconfig.yaml",
        }
    out_dir = EVALS_DIR / "baseline-results" / "promptfoo"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx",
        "--yes",
        "promptfoo@latest",
        "eval",
        "-c",
        str(cfg),
        "-o",
        str(out_dir / "results.json"),
    ]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    return {
        "status": "ok" if proc.returncode == 0 else "error",
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
        "config": str(cfg),
        "output": str(out_dir / "results.json"),
    }
