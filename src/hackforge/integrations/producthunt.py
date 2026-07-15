from __future__ import annotations

import os
from typing import Any

import httpx


API = "https://api.producthunt.com/v2/api/graphql"


def _token() -> str | None:
    return os.getenv("PRODUCTHUNT_ACCESS_TOKEN") or os.getenv("PH_ACCESS_TOKEN") or None


def search_posts(query: str, *, count: int = 5) -> list[dict[str, Any]]:
    token = _token()
    if not token or not query.strip():
        return []
    # Product Hunt GraphQL has limited search; use posts + topic-less filter via featured query as fallback
    gql = """
    query Search($q: String) {
      posts(first: 10, order: VOTES) {
        edges {
          node {
            name
            tagline
            url
            votesCount
            website
          }
        }
      }
    }
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(API, headers=headers, json={"query": gql, "variables": {"q": query}})
        if resp.status_code != 200:
            return []
        data = resp.json()
    edges = (((data.get("data") or {}).get("posts") or {}).get("edges")) or []
    q = query.lower()
    scored = []
    for e in edges:
        node = e.get("node") or {}
        blob = f"{node.get('name','')} {node.get('tagline','')}".lower()
        score = sum(1 for tok in q.split() if len(tok) > 3 and tok in blob)
        if score:
            scored.append((score, node))
    scored.sort(key=lambda x: -x[0])
    out = []
    for _, node in scored[:count]:
        out.append(
            {
                "name": node.get("name"),
                "tagline": node.get("tagline"),
                "url": node.get("url") or node.get("website"),
                "votes": node.get("votesCount"),
            }
        )
    return out
