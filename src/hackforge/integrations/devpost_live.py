from __future__ import annotations

import base64
import os
import re
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "HackForge/0.2 (+private research; collision audit)"}
BASE = "https://devpost.com"
GITHUB_API = "https://api.github.com"
_DEVPOST_PROJECT_URL = re.compile(
    r"https?://(?:www\.)?devpost\.com/software/[A-Za-z0-9_-]+",
    re.IGNORECASE,
)
_WAF_MARKERS = ("awswaf", "window.gokuprops", "awswafcookiedomainlist")


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


def search_projects(
    query: str,
    *,
    max_results: int = 20,
    client: httpx.Client | None = None,
    github_token: str | None = None,
) -> list[dict[str, Any]]:
    """Find real Devpost projects, with GitHub README discovery when Devpost serves WAF.

    The fallback does not invent project records. It searches public repositories and
    extracts literal Devpost project URLs from their READMEs, retaining the discovery
    repository on every row for provenance.
    """
    url = f"{BASE}/software/search?query={quote_plus(query)}"
    owned_client = client is None
    http = client or _client()
    direct_error = ""
    try:
        try:
            resp = http.get(url)
            if resp.status_code != 200:
                direct_error = f"Devpost returned HTTP {resp.status_code}"
            elif _is_waf_response(resp.text):
                direct_error = "Devpost returned an AWS WAF challenge"
            else:
                projects = _parse_gallery(resp.text, source_url=url)[:max_results]
                if projects:
                    return projects
                direct_error = "Devpost returned no project records"
        except httpx.HTTPError as exc:
            direct_error = f"Devpost request failed: {exc}"

        discovered = _discover_projects_from_github_readmes(
            query,
            max_results=max_results,
            client=http,
            token=github_token or os.getenv("GITHUB_TOKEN"),
        )
        if discovered:
            return discovered
        raise RuntimeError(
            f"{direct_error or 'Devpost search failed'}; public GitHub README discovery "
            "returned no literal Devpost project URLs. No mock or empty-data fallback was used."
        )
    finally:
        if owned_client:
            http.close()


def check_idea_exists(idea_description: str, *, max_results: int = 10) -> list[dict[str, Any]]:
    """Nearest public Devpost projects for an idea string (collision pre-check)."""
    return search_projects(idea_description, max_results=max_results)


def get_project(project_slug: str) -> dict[str, Any]:
    url = f"{BASE}/software/{project_slug}"
    with _client() as client:
        resp = client.get(url)
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    title_element = soup.find("h1") or soup.find("title")
    title = title_element.get_text(strip=True) if title_element else project_slug
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
            href_value = a.get("href")
            href = str(href_value[0] if isinstance(href_value, list) and href_value else href_value or "")
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
        link = card.select_one('a[href*="/software/"]') or card.find("a")
        if not link:
            continue
        href_value = link.get("href")
        href = str(href_value[0] if isinstance(href_value, list) and href_value else href_value or "")
        title = link.get_text(strip=True) or card.get_text(" ", strip=True)[:80]
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


def _is_waf_response(html: str) -> bool:
    lowered = html.lower()
    return any(marker in lowered for marker in _WAF_MARKERS)


def _discover_projects_from_github_readmes(
    query: str,
    *,
    max_results: int,
    client: httpx.Client,
    token: str | None,
) -> list[dict[str, Any]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": HEADERS["User-Agent"],
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    meaningful = [
        word.lower()
        for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]+", query)
        if len(word) >= 4 and word.lower() not in {"hackathon", "competition", "build", "with"}
    ]
    focused = " ".join(dict.fromkeys(meaningful[:4]))
    searches = [f"devpost {focused} in:readme" if focused else "devpost hackathon in:readme"]
    if searches[0] != "devpost hackathon in:readme":
        searches.append("devpost hackathon in:readme")

    errors: list[str] = []
    projects: list[dict[str, Any]] = []
    for search_query in searches:
        response = client.get(
            f"{GITHUB_API}/search/repositories",
            params={"q": search_query, "sort": "updated", "per_page": min(max(max_results * 5, 30), 50)},
            headers=headers,
        )
        if response.status_code in {403, 429}:
            errors.append(f"GitHub search rate limited with HTTP {response.status_code}")
            continue
        try:
            response.raise_for_status()
            rows = response.json().get("items") or []
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(f"GitHub search failed: {exc}")
            continue

        for row in rows:
            repository = str(row.get("full_name") or "")
            api_url = str(row.get("url") or "")
            if not repository or not api_url:
                continue
            branch = str(row.get("default_branch") or "main")
            raw_readme_url = f"https://raw.githubusercontent.com/{repository}/{branch}/README.md"
            raw_readme = client.get(raw_readme_url, headers={"User-Agent": HEADERS["User-Agent"]})
            if raw_readme.status_code == 200:
                content = raw_readme.text
            else:
                readme = client.get(f"{api_url}/readme", headers=headers)
                if readme.status_code in {403, 429}:
                    errors.append(f"GitHub README API rate limited with HTTP {readme.status_code}")
                    continue
                if readme.status_code != 200:
                    continue
                try:
                    payload = readme.json()
                    content = base64.b64decode(str(payload.get("content") or "")).decode(
                        "utf-8", "replace"
                    )
                except (ValueError, TypeError):
                    continue
            for project_url in dict.fromkeys(_DEVPOST_PROJECT_URL.findall(content)):
                slug = project_url.rstrip("/").rsplit("/", 1)[-1]
                projects.append(
                    {
                        "title": str(row.get("name") or slug),
                        "tagline": str(row.get("description") or ""),
                        "url": project_url,
                        "built_with": list(row.get("topics") or []),
                        "discovered_via": str(row.get("html_url") or f"https://github.com/{repository}"),
                        "discovery_method": "github-readme-literal-link",
                    }
                )
                if len(_dedupe(projects)) >= max_results:
                    return _dedupe(projects)[:max_results]
        if projects:
            break

    if errors and not projects:
        raise RuntimeError("; ".join(errors))
    return _dedupe(projects)[:max_results]


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
