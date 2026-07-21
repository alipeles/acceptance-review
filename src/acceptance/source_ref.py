"""Source references: a `TextSpan` links a value to the exact text it came from.

Lives in its own leaf module so both the review-state model (obligations link
to task text) and the requirement parser can use it without an import cycle.
`text == source[start:end]` always holds for a span produced from a source.
"""

from __future__ import annotations

from acceptance.model_base import PersistableModel


class TextSpan(PersistableModel):
    text: str
    start: int
    end: int


def find_span(source: str, quote: str) -> TextSpan | None:
    """Locate `quote` in `source` and return its span, or None if absent."""
    if not quote:
        return None
    idx = source.find(quote)
    if idx < 0:
        return None
    return TextSpan(text=quote, start=idx, end=idx + len(quote))
