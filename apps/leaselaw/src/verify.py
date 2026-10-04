"""Deterministic quote verification (literal corpus substrings)."""

from __future__ import annotations

import re

MIN_QUOTE = 20


def span_from_text(text: str, needle: str, min_len: int = MIN_QUOTE) -> str | None:
    """Return a verbatim substring of ``text`` covering ``needle``."""
    if not text or not needle:
        return None
    idx = text.find(needle)
    if idx >= 0:
        start, end = idx, idx + len(needle)
    else:
        pattern = r"\s+".join(re.escape(word) for word in needle.split())
        m = re.search(pattern, text, flags=re.I)
        if not m:
            return None
        start, end = m.start(), m.end()
    pad_start = max(0, start - 60)
    pad_end = min(len(text), end + 120)
    span = text[pad_start:pad_end].strip()
    if len(span) < min_len or span not in text:
        if text[start:end].strip() in text and len(text[start:end].strip()) >= min_len:
            return text[start:end].strip()
        return None
    return span


def is_literal_span(text: str, quoted_span: str) -> bool:
    if not quoted_span or quoted_span.startswith("["):
        return False
    return quoted_span in text
