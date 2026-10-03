from __future__ import annotations

import json
from typing import Any

from hackforge.collision.corpus_loader import collision_markdown, load_analogue_corpus
from hackforge.collision.embed_index import EmbedIndex, structural_text
from hackforge.models import Analogue, CandidateIdea, CollisionReport, SimilarityDims
from hackforge.providers import DryRunProvider, LLMProvider
from hackforge.utils import load_prompt

# Fields the auditor actually weighs: identity plus the user/problem/mechanism/
# data/action/demo dimensions named in the prompt. Sending every CandidateIdea
# field triples the payload with prose the audit never reads (requirement_satisfaction
# alone is ~14k chars per candidate), which historically pushed the request past the
# cap below and forced a mid-sentence truncation of the JSON.
_AUDIT_CANDIDATE_FIELDS = (
    "id",
    "working_title",
    "primary_user",
    "painful_workflow",
    "current_workaround",
    "imported_mechanism",
    "data_sources",
    "last_mile_action",
    "core_computation",
    "killer_demo",
    "visible_transformation",
    "hard_to_fake_advantage",
)

# Hard ceiling on the rendered request. Exceeding it fails loudly rather than
# slicing the payload: a truncated JSON object is unreadable and produced a
# non-terminating audit rather than a degraded one.
_MAX_PAYLOAD_CHARS = 120_000


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
    require_semantic: bool = False,
) -> list[dict[str, Any]]:
    index = index or EmbedIndex()
    hits: list[dict[str, Any]] = []
    if index.available():
        hits = index.search(candidate, k=k)
        if require_semantic and not hits:
            raise RuntimeError(
                f"Semantic collision index returned no analogues for {candidate.id}; "
                "no lexical fallback was used"
            )
    elif require_semantic:
        raise RuntimeError(
            f"Semantic collision index is unavailable at {index.index_dir}; "
            "run `hackforge corpus build-index`. No lexical fallback was used."
        )
    if not hits:
        # Explicit lexical mode over the real local corpus when the semantic index has no hits.
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
    from hackforge.integrations.devpost_live import check_idea_exists
    from hackforge.integrations.producthunt import search_posts

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
    provider: LLMProvider | None,
    candidates: list[CandidateIdea],
    *,
    k: int = 8,
    live_enrich: bool = True,
    use_llm: bool = True,
    supplemental_analogues: list[dict[str, Any]] | None = None,
    require_semantic: bool = False,
    exclude: list[str] | None = None,
) -> list[CollisionReport]:
    index = EmbedIndex()
    template, _ = load_prompt("collision-audit")
    reports: list[CollisionReport] = []

    retrieved_map: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        retrieved_map[c.id] = retrieve_analogues(
            c,
            k=k,
            index=index,
            live_enrich=live_enrich,
            require_semantic=require_semantic,
        )
        if supplemental_analogues:
            retrieved_map[c.id].extend(_rank_supplemental(c, supplemental_analogues, k=5))
        needles = [value.casefold().strip() for value in (exclude or []) if value.strip()]
        retrieved_map[c.id] = [
            hit for hit in retrieved_map[c.id]
            if not any(
                needle in str(hit.get(key) or "").casefold()
                for needle in needles for key in ("name", "title", "url")
            )
        ]

    if use_llm:
        if provider is None:
            raise RuntimeError("LLM collision audit was requested without a live provider")
        payload = {
            "candidates": [
                {
                    key: value
                    for key, value in c.model_dump().items()
                    if key in _AUDIT_CANDIDATE_FIELDS
                }
                for c in candidates
            ],
            "nearest_by_candidate": retrieved_map,
        }
        rendered = json.dumps(payload, ensure_ascii=False)
        if len(rendered) > _MAX_PAYLOAD_CHARS:
            raise RuntimeError(
                f"Collision audit payload is {len(rendered)} chars, over the "
                f"{_MAX_PAYLOAD_CHARS} limit; refusing to truncate JSON mid-object. "
                "Reduce the shortlist size or analogue depth."
            )
        try:
            schema = None if isinstance(provider, DryRunProvider) else _collision_schema(len(candidates))
            raw = provider.complete_json(template, rendered, schema=schema)
            items = raw if isinstance(raw, list) else (raw.get("reports") if isinstance(raw, dict) else [])
        except Exception:
            if not isinstance(provider, DryRunProvider):
                raise
            items = []
    else:
        items = []

    by_id: dict[str, CollisionReport] = {}
    required_fields = {
        "candidate_id",
        "nearest_analogues",
        "collision_risk",
        "observable_differentiator",
        "differentiator_is_substantive",
        "kill_recommendation",
        "notes",
    }
    for row_index, item in enumerate(items or []):
        if not isinstance(item, dict):
            if use_llm and not isinstance(provider, DryRunProvider):
                raise RuntimeError(f"collision auditor row {row_index} was not an object")
            continue
        missing_fields = required_fields - set(item)
        if missing_fields and use_llm and not isinstance(provider, DryRunProvider):
            raise RuntimeError(
                f"collision auditor row {row_index} omitted fields {sorted(missing_fields)}; "
                "no heuristic values were inserted"
            )
        cid = str(item.get("candidate_id") or "")
        if not cid:
            continue
        by_id[cid] = _parse_llm_report(item)

    if use_llm and not isinstance(provider, DryRunProvider):
        expected = {candidate.id for candidate in candidates}
        missing = expected - set(by_id)
        unexpected = set(by_id) - expected
        for bad_id in unexpected:
            by_id.pop(bad_id, None)
        # Incomplete model outputs are repaired with deterministic heuristics for the
        # missing IDs only. Fully empty live outputs remain fail-closed.
        if not by_id and expected:
            raise RuntimeError(
                "collision auditor returned no usable reports for the requested candidates; "
                "no heuristic fallback was used"
            )
        if missing or unexpected:
            # Keep going; the per-candidate loop below fills gaps heuristically.
            pass

    for c in candidates:
        if c.id in by_id:
            reports.append(by_id[c.id])
            continue
        reports.append(_heuristic_report(c, retrieved_map.get(c.id, [])))
    return reports


def _rank_supplemental(
    candidate: CandidateIdea,
    analogues: list[dict[str, Any]],
    *,
    k: int,
) -> list[dict[str, Any]]:
    candidate_tokens = {token for token in structural_text(candidate).lower().split() if len(token) > 3}
    ranked = []
    for analogue in analogues:
        target = " ".join(str(analogue.get(key) or "") for key in ("name", "problem", "mechanism", "action"))
        target_tokens = {token for token in target.lower().split() if len(token) > 3}
        similarity = len(candidate_tokens & target_tokens) / max(1, len(candidate_tokens | target_tokens))
        ranked.append((similarity, {**analogue, "similarity": similarity}))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item for score, item in ranked[:k] if score > 0]


def _collision_schema(count: int) -> dict[str, Any]:
    similarities = {
        "type": "object",
        "properties": {
            key: {"type": "boolean"}
            for key in ("same_user", "same_problem", "same_mechanism", "same_data", "same_action", "same_demo")
        },
        "required": [
            "same_user",
            "same_problem",
            "same_mechanism",
            "same_data",
            "same_action",
            "same_demo",
        ],
        "additionalProperties": False,
    }
    report = {
        "type": "object",
        "properties": {
            "candidate_id": {"type": "string"},
            "nearest_analogues": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "source": {"type": "string"},
                        "url": {"type": "string"},
                        "similarities": similarities,
                        "differences": {
                            "type": "array",
                            "maxItems": 2,
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["name", "source", "url", "similarities", "differences"],
                    "additionalProperties": False,
                },
            },
            "collision_risk": {"type": "string", "enum": ["low", "medium", "high"]},
            "observable_differentiator": {"type": "string"},
            "differentiator_is_substantive": {"type": "boolean"},
            "kill_recommendation": {"type": "boolean"},
            "notes": {"type": "string"},
        },
        "required": [
            "candidate_id",
            "nearest_analogues",
            "collision_risk",
            "observable_differentiator",
            "differentiator_is_substantive",
            "kill_recommendation",
            "notes",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "reports": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": report,
            }
        },
        "required": ["reports"],
        "additionalProperties": False,
    }


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
    reports = audit_collisions_engine(
        provider,
        ideas,
        live_enrich=live_enrich,
        use_llm=use_llm,
    )
    return reports, collision_markdown(reports)
