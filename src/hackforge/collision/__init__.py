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
    """Semantic/local/public analogue audit with optional strict index enforcement.

    A built FAISS index is used automatically when available. It is not a universal
    prerequisite because some competitions (for example grants, pitches, robotics,
    research, or private-domain challenges) may have little useful coverage in the
    bundled public-project corpus. Set HACKFORGE_REQUIRE_SEMANTIC_COLLISION=1 when a
    trusted workflow specifically requires a populated semantic index.
    """
    return audit_collisions_engine(
        provider,
        candidates,
        live_enrich=live_enrich,
        use_llm=True,
        supplemental_analogues=corpus,
        require_semantic=env_flag("HACKFORGE_REQUIRE_SEMANTIC_COLLISION", default=False),
    )


__all__ = [
    "audit_collisions",
    "collision_markdown",
    "load_analogue_corpus",
    "audit_collisions_engine",
]
