from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator


def langfuse_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


@contextmanager
def trace_stage(name: str, metadata: dict[str, Any] | None = None) -> Iterator[Any]:
    """Optional Langfuse span. No-op when keys are unset."""
    if not langfuse_enabled():
        yield None
        return
    try:
        from langfuse import Langfuse

        client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )
        trace = client.trace(name=f"hackforge.{name}", metadata=metadata or {})
        span = trace.span(name=name)
        yield span
        span.end()
        client.flush()
    except Exception:
        yield None
