from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def explicit_fixture_semantic_mode(monkeypatch: pytest.MonkeyPatch):
    """Unit tests opt out explicitly; trusted live runs require semantic collision search."""
    monkeypatch.setenv("HACKFORGE_USE_SENTENCE_TRANSFORMERS", "0")
    monkeypatch.setenv("HACKFORGE_REQUIRE_SEMANTIC_COLLISION", "0")
