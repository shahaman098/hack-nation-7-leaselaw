from __future__ import annotations

from typing import Any

from hackforge.collision.corpus_loader import collision_markdown, load_analogue_corpus
from hackforge.collision.embed_index import EmbedIndex, structural_text
from hackforge.models import Analogue, CandidateIdea, CollisionReport, SimilarityDims
from hackforge.providers import LLMProvider
from hackforge.utils import load_prompt


def dimensional_similarity(candidate: CandidateIdea, analogue: dict[str, Any]) -> SimilarityDims:
    """Heuristic dimensional overlap before LLM audit."""
    c_user = (candidate.primary_user or "").lower()
    c_problem = (candidate.painful_workflow or "").lower()
    c_mech = (candidate.imported_mechanism or "").lower()
    c_data = " ".join(candidate.data_sources).lower()
    c_action = (candidate.last_mile_action or "").lower()
    c_demo = (candidate.killer_demo or "").lower()

    a_user = str(analogue.get("user") or "").lower()
    a_problem = str(analogue.get("problem") or "").lower()
    a_mech = str(analogue.get("mechanism") or "").lower()
    a_data = str(analogue.get("data") or "").lower()
    a_action = str(analogue.get("action") or "").lower()
    a_demo = str(analogue.get("demo") or "").lower()

    def overlap(a: str, b: str, min_tok: int = 1) -> bool:
        at = {t for t in a.split() if len(t) > 3}
        bt = {t for t in b.split() if len(t) > 3}
        return len(at & bt) >= min_tok

    return SimilarityDims(
        same_user=overlap(c_user, a_user) or ("student" in c_user and "student" in a_user),
        same_problem=overlap(c_problem, a_problem, 2),
        same_mechanism=overlap(c_mech, a_mech, 1),
        same_data=bool(c_data and a_data and overlap(c_data, a_data)),
        same_action=overlap(c_action, a_action),
        same_demo=overlap(c_demo, a_demo),
    )


def risk_from_dims(sim: SimilarityDims, similarity: float) -> str:
    hits = sum(
        [
            sim.same_user,
            sim.same_problem,
            sim.same_mechanism,
            sim.same_data,
            sim.same_action,
            sim.same_demo,
        ]
    )
    if (sim.same_user and sim.same_problem and sim.same_mechanism) or (hits >= 4 and similarity >= 0.72):
        return "high"
    if hits >= 2 or similarity >= 0.65:
        return "medium"
    return "low"


def retrieve_analogues(
    candidate: CandidateIdea,
    *,
    k: int = 8,
    index: EmbedIndex | None = None,
    live_enrich: bool = True,
) -> list[dict[str, Any]]:
    index = index or EmbedIndex()
    hits: list[dict[str, Any]] = []
    if index.available():
        hits = index.search(candidate, k=k)
    if not hits:
        # Fallback: keyword scan local analogue corpus
        corpus = load_analogue_corpus()
        blob = structural_text(candidate).lower()
        scored = []
        for a in corpus:
            target = " ".join(str(a.get(x, "")) for x in ("name", "problem", "mechanism", "action")).lower()
            score = sum(1 for tok in blob.split() if len(tok) > 4 and tok in target)
            if score:
                scored.append((score, a))
        scored.sort(key=lambda x: -x[0])
        hits = [{**a, "similarity": min(0.99, s / 10)} for s, a in scored[:k]]

    if live_enrich:
        hits = _enrich_live(candidate, hits)
    return hits


def _enrich_live(candidate: CandidateIdea, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        from hackforge.integrations.devpost_live import check_idea_exists

        query = f"{candidate.working_title} {candidate.painful_workflow}"[:180]
        live = check_idea_exists(query, max_results=5)
        for item in live:
            hits.append(
                {
                    "name": item.get("title") or item.get("name"),
                    "source": "devpost-live",
                    "url": item.get("url") or "",
                    "user": "hackathon team",
                    "problem": item.get("tagline") or "",
                    "mechanism": " ".join(item.get("built_with") or []),
                    "data": "",
                    "action": "submission",
                    "demo": item.get("tagline") or "",
                    "similarity": 0.55,
                }
            )
    except Exception:
        pass
    try:
        from hackforge.integrations.producthunt import search_posts

        ph = search_posts(candidate.painful_workflow[:80] or candidate.working_title, count=3)
        for item in ph:
            hits.append(
                {
                    "name": item.get("name"),
                    "source": "producthunt",
                    "url": item.get("url") or "",
                    "user": "startup users",
                    "problem": item.get("tagline") or "",
                    "mechanism": "",
                    "data": "",
                    "action": "product",
                    "demo": item.get("tagline") or "",
                    "similarity": 0.5,
                }
            )
    except Exception:
        pass
    # Dedup by name
    seen = set()
    uniq = []
    for h in hits:
        key = (str(h.get("name") or ""), str(h.get("source") or ""))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
    return uniq[:12]


def audit_collisions_engine(
    provider: LLMProvider,
    candidates: list[CandidateIdea],
    *,
    k: int = 8,
    live_enrich: bool = True,
    use_llm: bool = True,
) -> list[CollisionReport]:
    index = EmbedIndex()
    template, _ = load_prompt("collision-audit")
    reports: list[CollisionReport] = []

    retrieved_map: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        retrieved_map[c.id] = retrieve_analogues(c, k=k, index=index, live_enrich=live_enrich)

    if use_llm:
        payload = {
            "candidates": [c.model_dump() for c in candidates],
            "nearest_by_candidate": retrieved_map,
        }
        try:
            raw = provider.complete_json(template, str(payload)[:120_000])
            items = raw if isinstance(raw, list) else (raw.get("reports") if isinstance(raw, dict) else [])
        except Exception:
            items = []
    else:
        items = []

    by_id: dict[str, CollisionReport] = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("candidate_id") or "")
        if not cid:
            continue
        by_id[cid] = _parse_llm_report(item)

    for c in candidates:
        if c.id in by_id:
            reports.append(by_id[c.id])
            continue
        reports.append(_heuristic_report(c, retrieved_map.get(c.id, [])))
    return reports


def _parse_llm_report(item: dict[str, Any]) -> CollisionReport:
    analogues = []
    for a in item.get("nearest_analogues") or []:
        if not isinstance(a, dict):
            continue
        sim = a.get("similarities") or {}
        analogues.append(
            Analogue(
                name=str(a.get("name") or "unknown"),
                source=str(a.get("source") or ""),
                url=str(a.get("url") or ""),
                similarities=SimilarityDims(
                    same_user=bool(sim.get("same_user")),
                    same_problem=bool(sim.get("same_problem")),
                    same_mechanism=bool(sim.get("same_mechanism")),
                    same_data=bool(sim.get("same_data")),
                    same_action=bool(sim.get("same_action")),
                    same_demo=bool(sim.get("same_demo")),
                ),
                differences=list(a.get("differences") or []),
            )
        )
    return CollisionReport(
        candidate_id=str(item.get("candidate_id") or ""),
        nearest_analogues=analogues,
        collision_risk=item.get("collision_risk") or "medium",
        observable_differentiator=str(item.get("observable_differentiator") or ""),
        differentiator_is_substantive=bool(item.get("differentiator_is_substantive")),
        kill_recommendation=bool(item.get("kill_recommendation")),
        notes=str(item.get("notes") or ""),
    )


def _heuristic_report(candidate: CandidateIdea, hits: list[dict[str, Any]]) -> CollisionReport:
    analogues = []
    worst = "low"
    for h in hits[:5]:
        sim = dimensional_similarity(candidate, h)
        risk = risk_from_dims(sim, float(h.get("similarity") or 0))
        if risk == "high":
            worst = "high"
        elif risk == "medium" and worst == "low":
            worst = "medium"
        analogues.append(
            Analogue(
                name=str(h.get("name") or "analogue"),
                source=str(h.get("source") or "index"),
                url=str(h.get("url") or ""),
                similarities=sim,
                differences=[f"similarity={h.get('similarity', 0):.3f}"],
            )
        )
    substantive = bool(candidate.hard_to_fake_advantage)
    kill = worst == "high" and not substantive
    return CollisionReport(
        candidate_id=candidate.id,
        nearest_analogues=analogues,
        collision_risk=worst,  # type: ignore[arg-type]
        observable_differentiator=candidate.hard_to_fake_advantage or candidate.killer_demo,
        differentiator_is_substantive=substantive,
        kill_recommendation=kill,
        notes="faiss+dimensional heuristic" if hits else "no index hits",
    )


def run_collide_on_ideas(
    ideas: list[CandidateIdea],
    provider: LLMProvider | None = None,
    *,
    live_enrich: bool = False,
    use_llm: bool = False,
) -> tuple[list[CollisionReport], str]:
    from hackforge.providers import DryRunProvider

    provider = provider or DryRunProvider({"collision": []})
    reports = audit_collisions_engine(
        provider,
        ideas,
        live_enrich=live_enrich,
        use_llm=use_llm and not isinstance(provider, DryRunProvider),
    )
    return reports, collision_markdown(reports)
