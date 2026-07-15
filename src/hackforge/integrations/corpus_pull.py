from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable

import httpx

from hackforge.paths import CORPUS_CACHE_DIR, HACKREP_DIR, REPO_ROOT
from hackforge.utils import write_json, write_text

SOURCES = ("alpha", "twango", "alvanlii", "hackrep", "local")

# Never pull Alpha-Hack strategy exemplars into ideation — corpus records only.
ALPHA_DATASET = "xenosaac/alphahack-devpost"
TWANGO_DATASET = "twangodev/devpost-hacks"
ALVANLII_DATASET = "alvanlii/devpost-hackathon-projects"

# HackRep Zenodo record (scripts + metadata); full 2.5GB dump is optional.
HACKREP_ZENODO_API = "https://zenodo.org/api/records/17572684"


def _cache_dir() -> Path:
    root = Path(os.getenv("HACKFORGE_CORPUS_CACHE", CORPUS_CACHE_DIR))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _normalize_record(rec: dict[str, Any], source: str) -> dict[str, Any]:
    title = str(rec.get("title") or rec.get("name") or "untitled")
    tagline = str(rec.get("tagline") or rec.get("brief_desc") or "")
    desc = str(rec.get("description") or rec.get("full_description") or rec.get("full_desc") or "")
    problem = tagline or desc[:280]
    is_winner = bool(rec.get("is_winner") or rec.get("prizes_won") or rec.get("prize"))
    return {
        "id": str(rec.get("project_id") or rec.get("id") or f"{source}:{title}")[:120],
        "name": title,
        "source": source,
        "url": str(rec.get("source_url") or rec.get("url") or rec.get("project_link") or ""),
        "user": "hackathon team",
        "problem": problem,
        "mechanism": str(
            rec.get("mechanism")
            or " ".join(rec.get("tech_tags") or rec.get("built_with") or rec.get("tags") or [])
        ),
        "data": "",
        "action": "submission demo",
        "demo": tagline or title,
        "is_winner": is_winner,
        "text_for_embed": " | ".join(
            x for x in [title, tagline, problem[:400], " ".join(rec.get("built_with") or rec.get("tags") or [])] if x
        ),
    }


def pull_alpha(limit: int = 5000, winners_only: bool = False) -> Path:
    """Pull Alpha-Hack Devpost project shards (corpus only — no strategy engine)."""
    from datasets import load_dataset

    out = _cache_dir() / "alpha_normalized.jsonl"
    # Prefer curated exemplars + project sample; fall back to features parquet if present
    records: list[dict[str, Any]] = []
    try:
        ds = load_dataset(ALPHA_DATASET, data_files="exemplars/top_100_winners.json", split="train")
        for row in ds:
            records.append(_normalize_record(dict(row), "alpha-exemplar"))
    except Exception:
        pass
    try:
        ds = load_dataset(ALPHA_DATASET, data_files="projects/projects_00.jsonl", split="train")
        for i, row in enumerate(ds):
            if i >= limit:
                break
            rec = _normalize_record(dict(row), "alpha")
            if winners_only and not rec.get("is_winner"):
                continue
            records.append(rec)
    except Exception as exc:
        # Minimal fallback from local reference if HF unavailable
        write_text(_cache_dir() / "alpha_error.txt", str(exc))
        ref = REPO_ROOT / "corpora" / "past-winners" / "reference-index.json"
        if ref.exists():
            for row in json.loads(ref.read_text(encoding="utf-8")):
                records.append(_normalize_record(row, "alpha-local-ref"))

    _write_jsonl(out, records)
    write_json(_cache_dir() / "alpha_meta.json", {"count": len(records), "path": str(out)})
    return out


def pull_twango(limit: int = 5000) -> Path:
    from datasets import load_dataset

    out = _cache_dir() / "twango_normalized.jsonl"
    ds = load_dataset(TWANGO_DATASET, split="train")
    records = []
    for i, row in enumerate(ds):
        if i >= limit:
            break
        records.append(_normalize_record(dict(row), "twango"))
    _write_jsonl(out, records)
    write_json(_cache_dir() / "twango_meta.json", {"count": len(records), "path": str(out)})
    return out


def pull_alvanlii(limit: int = 8000) -> Path:
    from datasets import load_dataset

    out = _cache_dir() / "alvanlii_normalized.jsonl"
    # Prefer parquet config if available
    try:
        ds = load_dataset(ALVANLII_DATASET, split="train")
    except Exception:
        ds = load_dataset(ALVANLII_DATASET, data_files="combined_hackathons.parquet", split="train")
    records = []
    for i, row in enumerate(ds):
        if i >= limit:
            break
        records.append(_normalize_record(dict(row), "alvanlii"))
    _write_jsonl(out, records)
    write_json(_cache_dir() / "alvanlii_meta.json", {"count": len(records), "path": str(out)})
    return out


def pull_hackrep() -> Path:
    """Download HackRep record metadata + scripts (not the full 2.5GB dump by default)."""
    HACKREP_DIR.mkdir(parents=True, exist_ok=True)
    meta_path = HACKREP_DIR / "zenodo_record.json"
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        resp = client.get(HACKREP_ZENODO_API)
        resp.raise_for_status()
        data = resp.json()
    write_json(meta_path, data)

    # Prefer small Scripts.zip if present
    files = data.get("files") or []
    scripts = next((f for f in files if "script" in str(f.get("key", "")).lower()), None)
    raw_dir = HACKREP_DIR / "raw"
    raw_dir.mkdir(exist_ok=True)
    if scripts and scripts.get("links", {}).get("self"):
        url = scripts["links"]["self"]
        dest = raw_dir / Path(scripts["key"]).name
        if not dest.exists():
            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                r = client.get(url)
                r.raise_for_status()
                dest.write_bytes(r.content)
    # Feasibility priors stub from description
    priors = {
        "source": "hackrep",
        "common_48h_stacks": ["javascript", "python", "react", "node", "firebase", "flask", "nextjs"],
        "notes": "Use only as feasibility prior — not as ideation examples.",
        "zenodo": "https://zenodo.org/records/17572684",
    }
    write_json(HACKREP_DIR / "feasibility_priors.json", priors)
    return meta_path


def pull_local() -> Path:
    """Normalize in-repo corpora JSON into cache jsonl."""
    from hackforge.collision.corpus_loader import load_analogue_corpus

    out = _cache_dir() / "local_normalized.jsonl"
    records = []
    for row in load_analogue_corpus():
        records.append(
            {
                "id": str(row.get("name") or row.get("id") or "local"),
                "name": str(row.get("name") or ""),
                "source": str(row.get("source") or "local"),
                "url": str(row.get("url") or ""),
                "user": str(row.get("user") or ""),
                "problem": str(row.get("problem") or ""),
                "mechanism": str(row.get("mechanism") or ""),
                "data": str(row.get("data") or ""),
                "action": str(row.get("action") or ""),
                "demo": str(row.get("demo") or ""),
                "is_winner": bool(row.get("is_winner")),
                "text_for_embed": " | ".join(
                    str(row.get(k) or "")
                    for k in ("user", "problem", "mechanism", "action", "demo", "name")
                ),
            }
        )
    _write_jsonl(out, records)
    return out


PULLERS: dict[str, Callable[..., Path]] = {
    "alpha": pull_alpha,
    "twango": pull_twango,
    "alvanlii": pull_alvanlii,
    "hackrep": pull_hackrep,
    "local": pull_local,
}


def pull_sources(
    sources: Iterable[str],
    *,
    limit: int = 5000,
    winners_only: bool = False,
) -> dict[str, str]:
    selected = list(sources)
    if "all" in selected:
        selected = list(SOURCES)
    results: dict[str, str] = {}
    for src in selected:
        if src not in PULLERS:
            raise ValueError(f"Unknown source: {src}. Choose from {SOURCES} or all")
        if src == "alpha":
            path = pull_alpha(limit=limit, winners_only=winners_only)
        elif src == "twango":
            path = pull_twango(limit=limit)
        elif src == "alvanlii":
            path = pull_alvanlii(limit=limit)
        else:
            path = PULLERS[src]()
        results[src] = str(path)
    return results


def iter_cached_records() -> Iterable[dict[str, Any]]:
    cache = _cache_dir()
    for path in sorted(cache.glob("*_normalized.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)


def build_index_from_cache(index_dir: Path | None = None, *, max_records: int | None = None) -> Path:
    from hackforge.collision.embed_index import EmbedIndex

    idx = EmbedIndex(index_dir)
    records = list(iter_cached_records())
    if max_records is not None:
        records = records[:max_records]
    if not records:
        # Ensure local at least
        pull_local()
        records = list(iter_cached_records())
    return idx.build(records)


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
