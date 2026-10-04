"""One-time Census Geocoder batch (cached). Optional enrichment for jurisdiction_stack."""

from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path

from .paths import APP_ROOT, require_starter

CACHE = APP_ROOT / "out" / "geocode_cache.csv"


def fetch_batch(addresses: list[dict], out_path: Path | None = None) -> Path:
    """Batch geocode up to 500 rows via Census Geocoder (no API key)."""
    out_path = out_path or CACHE
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Build batch file: id, street, city, state, zip
    lines = ["Unique ID,Street address,City,State,ZIP"]
    for a in addresses:
        lines.append(
            ",".join(
                [
                    a["address_id"],
                    json.dumps(a.get("street_address") or a.get("street") or ""),
                    json.dumps(a.get("postal_city") or ""),
                    a.get("state") or "",
                    a.get("zip") or "",
                ]
            )
        )
    payload = "\n".join(lines).encode("utf-8")
    url = (
        "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch"
        "?benchmark=Public_AR_Current&vintage=Current_Current&format=json"
    )
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "text/plain")
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
    # Response is JSON array per input row
    rows = json.loads(raw)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["address_id", "matched", "incorporated_place", "county", "state"])
        for item in rows:
            addr_id = item.get("id") or item.get("addressId")
            matches = item.get("result", {}).get("addressMatches") or []
            if not matches:
                w.writerow([addr_id, "no", "", "", ""])
                continue
            m = matches[0]
            geo = m.get("geographies", {})
            place = (geo.get("Incorporated Places") or [{}])[0].get("NAME", "")
            county = (geo.get("Counties") or [{}])[0].get("NAME", "")
            st = (geo.get("States") or [{}])[0].get("STUSAB", "")
            w.writerow([addr_id, "yes", place, county, st])
    return out_path


def load_geocode_index() -> dict[str, dict]:
    if not CACHE.exists():
        return {}
    idx: dict[str, dict] = {}
    with CACHE.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            idx[row["address_id"]] = row
    return idx


def ensure_cache() -> None:
    if CACHE.exists():
        return
    starter = require_starter()
    path = starter / "data" / "sample_addresses.csv"
    if not path.exists():
        return
    addrs: list[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            addrs.append(
                {
                    "address_id": row["address_id"],
                    "street_address": row["street_address"],
                    "postal_city": row["postal_city"],
                    "state": row["state"],
                    "zip": row["zip"],
                }
            )
    try:
        fetch_batch(addrs)
    except OSError:
        pass  # offline dev — static county map still applies
