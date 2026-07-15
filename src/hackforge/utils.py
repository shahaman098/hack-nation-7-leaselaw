from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from hackforge.paths import PROMPTS_DIR, PROMPT_VERSIONS, REPO_ROOT


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(text: str, max_len: int = 48) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return (s or "run")[:max_len]


def load_prompt(family: str, version: str | None = None) -> tuple[str, str]:
    ver = version or PROMPT_VERSIONS[family]
    path = PROMPTS_DIR / family / f"{ver}.md"
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt: {path}")
    return path.read_text(encoding="utf-8"), f"{family}/{ver}"


def render_prompt(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def make_run_dir(name: str, runs_root: Path | None = None) -> Path:
    from hackforge.paths import RUNS_DIR

    root = runs_root or RUNS_DIR
    root.mkdir(parents=True, exist_ok=True)
    slug = f"{date.today().isoformat()}-{slugify(name)}"
    path = root / slug
    n = 2
    while path.exists():
        path = root / f"{slug}-{n}"
        n += 1
    path.mkdir(parents=True, exist_ok=False)
    return path


def prompt_fingerprint() -> dict[str, str]:
    fps: dict[str, str] = {}
    for family, ver in PROMPT_VERSIONS.items():
        path = PROMPTS_DIR / family / f"{ver}.md"
        if path.exists():
            fps[f"{family}/{ver}"] = sha256_file(path)
    return fps


def corpora_version() -> str:
    archetype = REPO_ROOT / "corpora" / "crowded-archetypes" / "default.json"
    if archetype.exists():
        data = read_json(archetype)
        return str(data.get("version", sha256_file(archetype)[:12]))
    return "unknown"
