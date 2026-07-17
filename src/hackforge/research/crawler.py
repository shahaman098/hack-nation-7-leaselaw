from __future__ import annotations

import hashlib
import ipaddress
import re
import socket
from collections.abc import Iterable
from datetime import datetime, timezone
from html import unescape
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlparse, urlunparse

import httpx

from hackforge.models import EvidenceKind, EvidenceSource, EvidenceStatus

_RESEARCH_LINK = re.compile(r"rules?|resources?|faq|details?|criteria|prizes?|requirements?", re.I)
_TITLE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
_LINK = re.compile(r"(?is)<a[^>]+href=[\"']([^\"'#]+)[\"']")


def crawl_competition(
    start_url: str,
    *,
    max_pages: int = 8,
    timeout: float = 25.0,
    client: httpx.Client | None = None,
) -> list[EvidenceSource]:
    """Crawl a bounded set of official competition pages and record failures."""
    start = _canonical_url(start_url)
    owned_client = client is None
    try:
        _assert_safe_remote_url(start, resolve_dns=owned_client)
    except ValueError as exc:
        return [_failed_source(start, "blocked", None, str(exc))]
    host = urlparse(start).netloc.lower()
    queue = [start]
    seen: set[str] = set()
    sources: list[EvidenceSource] = []
    http = client or httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": "HackForge/0.4 competition-research"},
    )
    try:
        while queue and len(seen) < max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                response = http.get(url)
                status = response.status_code
                if status == 429:
                    sources.append(_failed_source(url, "rate_limited", status, "rate limited"))
                    continue
                if status != 200:
                    sources.append(
                        _failed_source(
                            url,
                            "blocked" if status == 202 else "failed",
                            status,
                            "non-success response; possible anti-bot challenge"
                            if status == 202
                            else f"unexpected HTTP {status}",
                        )
                    )
                    continue
                response.raise_for_status()
                if len(response.content) > 2_000_000:
                    sources.append(_failed_source(url, "blocked", status, "response exceeded 2 MB limit"))
                    continue
                html = response.text
                text = _safe_html_to_text(html)
                final_url = _canonical_url(str(response.url))
                try:
                    _assert_safe_remote_url(final_url, resolve_dns=owned_client)
                except ValueError as exc:
                    sources.append(_failed_source(final_url, "blocked", status, str(exc)))
                    continue
                title_match = _TITLE.search(html)
                title = unescape(_strip_tags(title_match.group(1))).strip() if title_match else final_url
                sources.append(
                    _source(
                        final_url,
                        title,
                        "official",
                        text[:12_000],
                        status,
                        verified=urlparse(final_url).netloc.lower() == host,
                    )
                )
                links = []
                for href in _LINK.findall(html):
                    candidate = _canonical_url(urljoin(final_url, unescape(href)))
                    parsed = urlparse(candidate)
                    if parsed.scheme in {"http", "https"} and parsed.netloc.lower() == host:
                        if _RESEARCH_LINK.search(parsed.path) or candidate == start:
                            links.append(candidate)
                for candidate in links:
                    if candidate not in seen and candidate not in queue:
                        queue.append(candidate)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                sources.append(_failed_source(url, "failed", status, str(exc)))
            except httpx.HTTPError as exc:
                sources.append(_failed_source(url, "failed", None, str(exc)))
    finally:
        if owned_client:
            http.close()
    return _deduplicate_sources(sources)


def search_github_projects(
    competition_name: str,
    *,
    max_results: int = 12,
    timeout: float = 20.0,
    client: httpx.Client | None = None,
    token: str | None = None,
) -> list[EvidenceSource]:
    """Use public GitHub repositories only as collision evidence."""
    query = f'"{competition_name}" in:name,description,readme'
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "HackForge/0.4 collision-research",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    owned_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True, headers=headers)
    endpoint = "https://api.github.com/search/repositories"
    try:
        response = http.get(endpoint, params={"q": query, "sort": "updated", "per_page": max_results})
        if response.status_code == 429 or response.status_code == 403:
            return [_failed_source(str(response.url), "rate_limited", response.status_code, "GitHub rate limit")]
        response.raise_for_status()
        rows = response.json().get("items") or []
        output: list[EvidenceSource] = []
        for row in rows[:max_results]:
            url = str(row.get("html_url") or "")
            if not url:
                continue
            description = str(row.get("description") or "")
            topics = ", ".join(row.get("topics") or [])
            excerpt = f"{description}\nTopics: {topics}\nUpdated: {row.get('updated_at') or ''}".strip()
            output.append(
                _source(
                    url,
                    str(row.get("full_name") or row.get("name") or url),
                    "github",
                    excerpt,
                    response.status_code,
                    verified=True,
                )
            )
        return output
    except (httpx.HTTPError, ValueError) as exc:
        return [_failed_source(endpoint, "failed", None, str(exc), source_kind="github")]
    finally:
        if owned_client:
            http.close()


def search_devpost_projects(
    query: str,
    *,
    max_results: int = 12,
) -> list[EvidenceSource]:
    """Retrieve public Devpost projects as first-class, provenance-bearing evidence."""
    endpoint = f"https://devpost.com/software/search?query={quote_plus(query)}"
    try:
        from hackforge.integrations.devpost_live import search_projects

        rows = search_projects(query, max_results=max_results)
        output: list[EvidenceSource] = []
        for row in rows[:max_results]:
            url = str(row.get("url") or "")
            if not url:
                continue
            title = str(row.get("title") or row.get("name") or url)
            tagline = str(row.get("tagline") or "")
            built_with = ", ".join(str(item) for item in (row.get("built_with") or []))
            discovered_via = str(row.get("discovered_via") or "")
            discovery = f"\nDiscovered via public repository: {discovered_via}" if discovered_via else ""
            excerpt = f"{tagline}\nBuilt with: {built_with}{discovery}".strip()
            output.append(_source(url, title, "devpost", excerpt, 200, verified=True))
        return output
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        kind: EvidenceStatus = "rate_limited" if status in {403, 429} else "failed"
        return [_failed_source(endpoint, kind, status, str(exc), source_kind="devpost")]
    except (ImportError, httpx.HTTPError, ValueError, RuntimeError) as exc:
        return [_failed_source(endpoint, "failed", None, str(exc), source_kind="devpost")]


def evidence_text(sources: Iterable[EvidenceSource], *, max_chars: int = 120_000) -> str:
    blocks: list[str] = []
    consumed = 0
    for source in sources:
        if source.fetch_status != "ok" or not source.excerpt:
            continue
        block = (
            f"<UNTRUSTED_EVIDENCE id={source.id!r} url={source.url!r}>\n"
            f"{source.excerpt}\n</UNTRUSTED_EVIDENCE>"
        )
        if consumed + len(block) > max_chars:
            remaining = max_chars - consumed
            if remaining > 200:
                blocks.append(block[:remaining])
            break
        blocks.append(block)
        consumed += len(block)
    return "\n\n".join(blocks)


def input_evidence(text: str, source: str) -> EvidenceSource:
    return _source(source, source, "input", text[:120_000], None, verified=True)


def _source(
    url: str,
    title: str,
    source_kind: EvidenceKind,
    excerpt: str,
    http_status: int | None,
    *,
    verified: bool,
) -> EvidenceSource:
    digest = hashlib.sha256(f"{url}\n{excerpt}".encode()).hexdigest()
    return EvidenceSource(
        id=f"src-{digest[:12]}",
        url=url,
        title=title,
        source_kind=source_kind,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        excerpt=excerpt,
        fetch_status="ok",
        http_status=http_status,
        content_hash=digest,
        verified=verified,
    )


def _failed_source(
    url: str,
    status: EvidenceStatus,
    http_status: int | None,
    error: str,
    *,
    source_kind: EvidenceKind = "official",
) -> EvidenceSource:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return EvidenceSource(
        id=f"src-{digest[:12]}",
        url=url,
        title=url,
        source_kind=source_kind,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        fetch_status=status,
        http_status=http_status,
        error=error[:1000],
        content_hash="",
        verified=False,
    )


def _safe_html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(?:script|style|noscript|svg)[^>]*>.*?</(?:script|style|noscript|svg)>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    return re.sub(r"\s+", " ", unescape(_strip_tags(html))).strip()


def _strip_tags(html: str) -> str:
    return re.sub(r"(?is)<[^>]+>", " ", html)


def _canonical_url(url: str) -> str:
    parsed = urlparse(url)
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parsed.query) if not k.lower().startswith("utm_")))
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", query, ""))


def _assert_safe_remote_url(url: str, *, resolve_dns: bool) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only public HTTP(S) competition URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are blocked")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("local network URLs are blocked")
    addresses: set[str] = set()
    try:
        addresses.add(str(ipaddress.ip_address(hostname)))
    except ValueError:
        if resolve_dns:
            try:
                addresses.update(str(item[4][0]).split("%", 1)[0] for item in socket.getaddrinfo(hostname, parsed.port or 443))
            except socket.gaierror as exc:
                raise ValueError(f"competition hostname could not be resolved: {hostname}") from exc
    for raw_address in addresses:
        address = ipaddress.ip_address(raw_address)
        if not address.is_global:
            raise ValueError(f"private, local, or reserved address is blocked: {address}")


def _deduplicate_sources(sources: list[EvidenceSource]) -> list[EvidenceSource]:
    output: list[EvidenceSource] = []
    seen: set[tuple[str, str]] = set()
    for source in sources:
        key = (_canonical_url(source.url), source.content_hash)
        if key not in seen:
            seen.add(key)
            output.append(source)
    return output
