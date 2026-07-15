from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "HackForge/0.2 (+private research; collision audit)"}
BASE = "https://devpost.com"


def _client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0)


def search_hackathons(query: str, *, status: str = "open", max_results: int = 10) -> list[dict[str, Any]]:
    """Uses Devpost public hackathon JSON API when available."""
    params = {"search": query, "status[]": status}
    with _client() as client:
        resp = client.get(f"{BASE}/api/hackathons", params=params)
        if resp.status_code != 200:
            return []
        data = resp.json()
    hackathons = data.get("hackathons") or data.get("results") or []
    out = []
    for h in hackathons[:max_results]:
        out.append(
            {
                "name": h.get("title") or h.get("name"),
                "slug": h.get("id") or h.get("slug"),
                "url": h.get("url") or h.get("submission_gallery_url"),
                "participants": h.get("registrations_count"),
                "open_state": h.get("open_state"),
                "submission_count": h.get("submission_count"),
            }
        )
    return out


def get_winners(hackathon_slug: str, *, max_results: int = 40) -> list[dict[str, Any]]:
    """Scrape gallery / winners for a hackathon subdomain or slug."""
    urls = [
        f"https://{hackathon_slug}.devpost.com/project-gallery?sorting=winner",
        f"https://{hackathon_slug}.devpost.com/project-gallery",
        f"{BASE}/software/search?query={quote_plus(hackathon_slug)}",
    ]
    projects: list[dict[str, Any]] = []
    with _client() as client:
        for url in urls:
            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    continue
                projects.extend(_parse_gallery(resp.text, source_url=url))
                if projects:
                    break
            except Exception:
                continue
    return projects[:max_results]


def search_projects(query: str, *, max_results: int = 20) -> list[dict[str, Any]]:
    url = f"{BASE}/software/search?query={quote_plus(query)}"
    with _client() as client:
        resp = client.get(url)
        resp.raise_for_status()
        return _parse_gallery(resp.text, source_url=url)[:max_results]


def check_idea_exists(idea_description: str, *, max_results: int = 10) -> list[dict[str, Any]]:
    """Nearest public Devpost projects for an idea string (collision pre-check)."""
    return search_projects(idea_description, max_results=max_results)


def get_project(project_slug: str) -> dict[str, Any]:
    url = f"{BASE}/software/{project_slug}"
    with _client() as client:
        resp = client.get(url)
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    title = (soup.find("h1") or soup.find("title")).get_text(strip=True) if soup.find("h1") or soup.find("title") else project_slug
    tagline_el = soup.select_one("#software-tagline, .software-tagline, p.large")
    tagline = tagline_el.get_text(strip=True) if tagline_el else ""
    built = [a.get_text(strip=True) for a in soup.select(".cp-tag, .software-tags a, #built-with a")]
    return {
        "title": title,
        "tagline": tagline,
        "url": url,
        "built_with": built,
        "slug": project_slug,
    }


def crowding_hints_for_query(query: str) -> dict[str, list[str]]:
    """Lightweight crowd signals for Pass 1 (not winner prose dumps)."""
    projects = search_projects(query, max_results=15)
    high = []
    for p in projects:
        title = (p.get("title") or "").lower()
        if any(w in title for w in ("tutor", "chatbot", "summar", "resume", "mental")):
            high.append(p.get("title") or title)
    return {
        "high_collision_seen_on_devpost": high[:8],
        "recent_similar_titles": [p.get("title") or "" for p in projects[:8]],
    }


def _parse_gallery(html: str, source_url: str = "") -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(".gallery-item, .software-entry, li.software, .block-wrapper")
    out: list[dict[str, Any]] = []
    if not cards:
        # Fallback: any software links
        for a in soup.select('a[href*="/software/"]')[:30]:
            href = a.get("href") or ""
            if "/software/" not in href:
                continue
            out.append(
                {
                    "title": a.get_text(strip=True) or href.rsplit("/", 1)[-1],
                    "tagline": "",
                    "url": urljoin(BASE, href),
                    "built_with": [],
                }
            )
        return _dedupe(out)

    for card in cards:
        a = card.select_one('a[href*="/software/"]') or card.find("a")
        if not a:
            continue
        href = a.get("href") or ""
        title = a.get_text(strip=True) or card.get_text(" ", strip=True)[:80]
        tag = card.select_one(".tagline, .software-entry-name + p, p")
        out.append(
            {
                "title": title,
                "tagline": tag.get_text(strip=True) if tag else "",
                "url": urljoin(source_url or BASE, href),
                "built_with": [t.get_text(strip=True) for t in card.select(".cp-tag, .tag")],
            }
        )
    return _dedupe(out)


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    uniq = []
    for it in items:
        key = it.get("url") or it.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(it)
    return uniq
