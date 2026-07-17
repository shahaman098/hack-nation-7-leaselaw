from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from hackforge.paths import PROMPT_VERSIONS, PROMPTS_DIR, REPO_ROOT


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
    _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str) -> None:
    _atomic_write(path, text if text.endswith("\n") else text + "\n")


def _atomic_write(path: Path, text: str) -> None:
    """Commit an artifact atomically so interrupted runs never leave truncated JSON/HTML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


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
    path.chmod(0o700)
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
