from __future__ import annotations

from typing import Any

from hackforge.collision.corpus_loader import collision_markdown, load_analogue_corpus
from hackforge.collision.engine import audit_collisions_engine
from hackforge.models import CandidateIdea, CollisionReport
from hackforge.providers import LLMProvider
from hackforge.utils import env_flag


def audit_collisions(
    provider: LLMProvider,
    candidates: list[CandidateIdea],
    corpus: list[dict[str, Any]] | None = None,
    *,
    live_enrich: bool = True,
) -> list[CollisionReport]:
    """FAISS prefilter + dimensional scores + LLM auditor."""
    return audit_collisions_engine(
        provider,
        candidates,
        live_enrich=live_enrich,
        use_llm=True,
        supplemental_analogues=corpus,
        require_semantic=env_flag("HACKFORGE_REQUIRE_SEMANTIC_COLLISION", default=True),
    )


__all__ = [
    "audit_collisions",
    "collision_markdown",
    "load_analogue_corpus",
    "audit_collisions_engine",
]
