from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from hackforge.models import CompetitionBrief, CrowdingMap, FactClaim, InferenceClaim, JudgingCriterion
from hackforge.paths import CORPORA_DIR
from hackforge.providers import LLMProvider
from hackforge.utils import load_prompt, read_json, render_prompt


def load_default_blacklist() -> dict:
    path = CORPORA_DIR / "crowded-archetypes" / "default.json"
    return read_json(path)


def ingest_file(path: Path) -> tuple[str, list[str]]:
    text = path.read_text(encoding="utf-8")
    return text, [str(path.resolve())]


def ingest_url(url: str, timeout: float = 30.0) -> tuple[str, list[str]]:
    headers = {"User-Agent": "HackForge/0.1 (+private research lab)"}
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        text = resp.text
        if "html" in content_type.lower():
            text = _html_to_text(text)
    return text, [url]


def _html_to_text(html: str) -> str:
    # Lightweight, dependency-free extraction for MVP
    html = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()


def build_competition_brief(
    provider: LLMProvider,
    raw_text: str,
    *,
    source_urls: list[str] | None = None,
    team_size: str | None = None,
    deadline: str | None = None,
    skills: str | None = None,
) -> CompetitionBrief:
    blacklist = load_default_blacklist()
    template, _ = load_prompt("competition-research")
    system = template
    user_parts = [
        "Hackathon materials:",
        raw_text[:120_000],
        "",
        "Default overcrowding seed blacklist (merge and refine):",
        str(blacklist),
    ]
    if team_size:
        user_parts.append(f"\nTeam size constraint: {team_size}")
    if deadline:
        user_parts.append(f"Deadline constraint: {deadline}")
    if skills:
        user_parts.append(f"Available skills/infrastructure: {skills}")

    data = provider.complete_json(system, "\n".join(user_parts))
    if not isinstance(data, dict):
        raise ValueError("Competition research did not return a JSON object")

    crowding_raw = data.get("crowding") or {}
    crowding = CrowdingMap(
        high_collision=list(crowding_raw.get("high_collision") or blacklist.get("high_collision", [])),
        medium_collision=list(crowding_raw.get("medium_collision") or blacklist.get("medium_collision", [])),
        potentially_underexplored=list(
            crowding_raw.get("potentially_underexplored")
            or blacklist.get("potentially_underexplored_seeds", [])
        ),
        do_not_build=list(
            crowding_raw.get("do_not_build")
            or blacklist.get("do_not_build_structural_twins", [])
        ),
    )

    facts = [FactClaim(**f) if isinstance(f, dict) else FactClaim(claim=str(f), source="unknown") for f in data.get("facts", [])]
    inference = [
        InferenceClaim(**i) if isinstance(i, dict) else InferenceClaim(claim=str(i), rationale="")
        for i in data.get("inference", [])
    ]
    criteria = [
        JudgingCriterion(**c) if isinstance(c, dict) else JudgingCriterion(name=str(c), weight_or_priority="unspecified")
        for c in data.get("judging_criteria", [])
    ]

    name = data.get("name") or _guess_name(raw_text, source_urls)
    brief = CompetitionBrief(
        name=name,
        slug=data.get("slug") or "",
        source_urls=source_urls or data.get("source_urls") or [],
        theme=data.get("theme") or "",
        tracks=list(data.get("tracks") or []),
        sponsors=list(data.get("sponsors") or []),
        deadline=deadline or data.get("deadline"),
        team_size=team_size or data.get("team_size"),
        required_or_encouraged_tech=list(data.get("required_or_encouraged_tech") or []),
        prizes=list(data.get("prizes") or []),
        facts=facts,
        inference=inference,
        missing=list(data.get("missing") or []),
        potentially_stale=list(data.get("potentially_stale") or []),
        judging_criteria=criteria,
        sponsor_capabilities=list(data.get("sponsor_capabilities") or []),
        available_datasets=list(data.get("available_datasets") or []),
        crowding=crowding,
        sanitized_brief=data.get("sanitized_brief") or "",
    )
    if not brief.sanitized_brief:
        brief.sanitized_brief = _fallback_sanitized_brief(brief)
    if not brief.slug:
        from hackforge.utils import slugify

        brief.slug = slugify(brief.name)
    return brief


def enrich_brief_with_live_crowding(
    brief: CompetitionBrief,
    *,
    force: bool = False,
) -> CompetitionBrief:
    """Merge Devpost crowd signals into blacklist labels only (no winner prose)."""
    from hackforge.utils import env_flag

    if not force and not env_flag("HACKFORGE_LIVE_RESEARCH"):
        return brief
    try:
        from hackforge.integrations.devpost_live import crowding_hints_for_query

        q = brief.theme or brief.name
        hints = crowding_hints_for_query(q)
        for title in hints.get("high_collision_seen_on_devpost") or []:
            label = f"Devpost-similar: {title}"
            if label not in brief.crowding.high_collision:
                brief.crowding.high_collision.append(label)
        for title in hints.get("recent_similar_titles") or []:
            label = f"Recent similar title: {title}"
            if label and label not in brief.crowding.medium_collision:
                brief.crowding.medium_collision.append(label)
    except Exception:
        pass
    return brief


def _guess_name(raw_text: str, source_urls: list[str] | None) -> str:
    for line in raw_text.splitlines()[:20]:
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:80]
    if source_urls:
        host = urlparse(source_urls[0]).netloc
        return host or "unnamed-hackathon"
    return "unnamed-hackathon"


def _fallback_sanitized_brief(brief: CompetitionBrief) -> str:
    parts = [
        f"Competition: {brief.name}",
        f"Theme: {brief.theme}" if brief.theme else "",
        f"Tracks: {', '.join(brief.tracks)}" if brief.tracks else "",
        f"Sponsors: {', '.join(brief.sponsors)}" if brief.sponsors else "",
        "Judging: "
        + "; ".join(f"{c.name} ({c.weight_or_priority})" for c in brief.judging_criteria),
        "Do not build: " + "; ".join(brief.crowding.do_not_build[:12]),
        "High collision: " + "; ".join(brief.crowding.high_collision[:12]),
    ]
    return "\n".join(p for p in parts if p)


def research_markdown(brief: CompetitionBrief) -> str:
    lines = [
        f"# Verified research: {brief.name}",
        "",
        "## Facts",
    ]
    for f in brief.facts:
        lines.append(f"- [{f.confidence}] {f.claim} _(source: {f.source})_")
    lines += ["", "## Inference"]
    for i in brief.inference:
        lines.append(f"- {i.claim} — {i.rationale}")
    lines += ["", "## Missing"]
    for m in brief.missing:
        lines.append(f"- {m}")
    lines += ["", "## Potentially stale"]
    for s in brief.potentially_stale:
        lines.append(f"- {s}")
    lines += ["", "## Crowding map"]
    lines.append("### High collision")
    for x in brief.crowding.high_collision:
        lines.append(f"- {x}")
    lines.append("### Medium collision")
    for x in brief.crowding.medium_collision:
        lines.append(f"- {x}")
    lines.append("### Potentially underexplored")
    for x in brief.crowding.potentially_underexplored:
        lines.append(f"- {x}")
    lines.append("### Do not build")
    for x in brief.crowding.do_not_build:
        lines.append(f"- {x}")
    return "\n".join(lines)
