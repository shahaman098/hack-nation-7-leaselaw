from __future__ import annotations

import base64
import html as html_lib
import os
import re
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx

HEADERS = {"User-Agent": "HackForge/0.5 (+private competition research; optional collision audit)"}
BASE = "https://devpost.com"
GITHUB_API = "https://api.github.com"
_DEVPOST_PROJECT_URL = re.compile(
    r"https?://(?:www\.)?devpost\.com/software/[A-Za-z0-9_-]+",
    re.IGNORECASE,
)
_WAF_MARKERS = ("awswaf", "window.gokuprops", "awswafcookiedomainlist")
_TAG_RE = re.compile(r"(?is)<[^>]+>")
_SOFTWARE_LINK_RE = re.compile(
    r'''(?is)<a\b[^>]*href=["']([^"']*/software/[A-Za-z0-9_-]+/?)["'][^>]*>(.*?)</a>'''
)


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
    for hackathon in hackathons[:max_results]:
        out.append(
            {
                "name": hackathon.get("title") or hackathon.get("name"),
                "slug": hackathon.get("id") or hackathon.get("slug"),
                "url": hackathon.get("url") or hackathon.get("submission_gallery_url"),
                "participants": hackathon.get("registrations_count"),
                "open_state": hackathon.get("open_state"),
                "submission_count": hackathon.get("submission_count"),
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

    HTML parsing has no mandatory third-party parser dependency. If BeautifulSoup is
    installed via the optional collision extras it is used for richer extraction;
    otherwise a conservative stdlib/regex parser extracts only literal project links.

    The fallback never invents project records. It searches public repositories and
    extracts literal Devpost project URLs from their READMEs, retaining provenance.
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
    soup = _optional_soup(resp.text)
    if soup is not None:
        title_element = soup.find("h1") or soup.find("title")
        title = title_element.get_text(strip=True) if title_element else project_slug
        tagline_el = soup.select_one("#software-tagline, .software-tagline, p.large")
        tagline = tagline_el.get_text(strip=True) if tagline_el else ""
        built = [anchor.get_text(strip=True) for anchor in soup.select(".cp-tag, .software-tags a, #built-with a")]
    else:
        title = _first_text_tag(resp.text, "h1") or _first_text_tag(resp.text, "title") or project_slug
        tagline = ""
        built = []
    return {
        "title": title,
        "tagline": tagline,
        "url": url,
        "built_with": built,
        "slug": project_slug,
    }


def crowding_hints_for_query(query: str) -> dict[str, list[str]]:
    """Lightweight crowd signals for optional public-project enrichment."""
    projects = search_projects(query, max_results=15)
    return {
        "high_collision_seen_on_devpost": [],
        "recent_similar_titles": [project.get("title") or "" for project in projects[:8]],
    }


def _optional_soup(html: str) -> Any | None:
    """Return BeautifulSoup only when optional parser extras are installed."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def _parse_gallery(html: str, source_url: str = "") -> list[dict[str, Any]]:
    soup = _optional_soup(html)
    if soup is not None:
        cards = soup.select(".gallery-item, .software-entry, li.software, .block-wrapper")
        out: list[dict[str, Any]] = []
        if not cards:
            for anchor in soup.select('a[href*="/software/"]')[:30]:
                href_value = anchor.get("href")
                href = str(
                    href_value[0]
                    if isinstance(href_value, list) and href_value
                    else href_value or ""
                )
                if "/software/" not in href:
                    continue
                out.append(
                    {
                        "title": anchor.get_text(strip=True) or href.rstrip("/").rsplit("/", 1)[-1],
                        "tagline": "",
                        "url": urljoin(source_url or BASE, href),
                        "built_with": [],
                    }
                )
            return _dedupe(out)

        for card in cards:
            link = card.select_one('a[href*="/software/"]') or card.find("a")
            if not link:
                continue
            href_value = link.get("href")
            href = str(
                href_value[0]
                if isinstance(href_value, list) and href_value
                else href_value or ""
            )
            title = link.get_text(strip=True) or card.get_text(" ", strip=True)[:80]
            tag = card.select_one(".tagline, .software-entry-name + p, p")
            out.append(
                {
                    "title": title,
                    "tagline": tag.get_text(strip=True) if tag else "",
                    "url": urljoin(source_url or BASE, href),
                    "built_with": [tag_node.get_text(strip=True) for tag_node in card.select(".cp-tag, .tag")],
                }
            )
        return _dedupe(out)

    # Conservative dependency-free fallback: only literal /software/ anchors.
    out = []
    for href, body in _SOFTWARE_LINK_RE.findall(html)[:30]:
        text = _clean_html_text(body)
        out.append(
            {
                "title": text or href.rstrip("/").rsplit("/", 1)[-1],
                "tagline": "",
                "url": urljoin(source_url or BASE, href),
                "built_with": [],
            }
        )
    return _dedupe(out)


def _first_text_tag(document: str, tag: str) -> str:
    match = re.search(
        rf"(?is)<{re.escape(tag)}\b[^>]*>(.*?)</{re.escape(tag)}>",
        document,
    )
    return _clean_html_text(match.group(1)) if match else ""


def _clean_html_text(value: str) -> str:
    return " ".join(html_lib.unescape(_TAG_RE.sub(" ", value)).split())


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
            params={
                "q": search_query,
                "sort": "updated",
                "per_page": min(max(max_results * 5, 30), 50),
            },
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
                        "discovered_via": str(
                            row.get("html_url") or f"https://github.com/{repository}"
                        ),
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
    unique = []
    for item in items:
        key = item.get("url") or item.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
