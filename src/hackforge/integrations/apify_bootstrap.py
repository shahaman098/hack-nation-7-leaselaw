from __future__ import annotations

import os
from typing import Any

import httpx

from hackforge.paths import CORPUS_CACHE_DIR
from hackforge.utils import write_json


def _token() -> str | None:
    return os.getenv("APIFY_TOKEN") or os.getenv("APIFY_API_TOKEN") or None


def pull_gallery(hackathon_url: str, *, max_projects: int = 50) -> list[dict[str, Any]]:
    """Optional Apify hackathon gallery bootstrap when APIFY_TOKEN is set."""
    token = _token()
    if not token:
        return []
    actor = os.getenv("APIFY_ACTOR", "gabrielaxy/hackathon-winner-repo-extractor")
    run_url = f"https://api.apify.com/v2/acts/{actor}/runs?token={token}"
    payload = {"hackathonUrl": hackathon_url, "maxProjects": max_projects}
    with httpx.Client(timeout=120.0) as client:
        run = client.post(run_url, json=payload)
        if run.status_code >= 400:
            return []
        run_data = run.json().get("data") or {}
        dataset_id = run_data.get("defaultDatasetId")
        if not dataset_id:
            return []
        items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={token}"
        items = client.get(items_url)
        if items.status_code >= 400:
            return []
        data = items.json()
    CORPUS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(CORPUS_CACHE_DIR / "apify_last_gallery.json", data if isinstance(data, list) else [data])
    return data if isinstance(data, list) else []
