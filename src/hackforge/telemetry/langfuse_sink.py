from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


def langfuse_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


@contextmanager
def trace_stage(name: str, metadata: dict[str, Any] | None = None) -> Iterator[Any]:
    """Optional Langfuse span. No-op when keys are unset."""
    if not langfuse_enabled():
        yield None
        return
    from langfuse import Langfuse

    client = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
    )
    trace_factory = client.trace  # type: ignore[attr-defined]
    trace = trace_factory(name=f"hackforge.{name}", metadata=metadata or {})
    span = trace.span(name=name)
    try:
        yield span
    finally:
        span.end()
        client.flush()
