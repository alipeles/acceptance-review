"""What each candidate response schema costs, in bytes on the wire.

Builds the real registry from a real task file, then renders four response
schemas through `inline_schema_refs` exactly as `llm.py` sends them:

  today        the current `_Decomposition`, requirement_id enum'd to the batch
  slots        one required field per requirement id (the shape proposed as the
               fix for the disposition count)
  slots+quote  the same, with each requirement's obligations restricted to
               quoting that requirement's own sentences
  single+quote one requirement per call, with the same quote enum

Run from the repo root with `.venv/bin/python`.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Literal

from pydantic import create_model

from acceptance.llm import StrictResponseModel, inline_schema_refs
from acceptance.requirement.obligations import (
    _DecomposedObligation,
    _Decomposition,
    _NoObligation,
    _OpenQuestion,
    _RaisedOpenQuestion,
    _Yielded,
)
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import parse_task_file
from acceptance.supplied_ids import constrain

SENTENCE = re.compile(r"(?<=[.;:])\s+")


def sentences(text: str) -> list[str]:
    parts = [" ".join(part.split()) for part in SENTENCE.split(text)]
    whole = " ".join(text.split())
    out = [part for part in parts if len(part) > 12]
    return out + ([whole] if whole not in out else [])


def rendered(model: type) -> int:
    return len(json.dumps(inline_schema_refs(model.model_json_schema())))


def quote_scoped(requirement_id: str, quotes: list[str]) -> type:
    """A disposition for one requirement whose obligations may only quote it."""
    obligation = create_model(
        f"Obligation_{requirement_id}",
        __base__=_DecomposedObligation,
        source_quote=(Literal[tuple(quotes)], ...),
    )
    yielded = create_model(
        f"Yielded_{requirement_id}",
        __base__=_Yielded,
        requirement_id=(Literal[requirement_id], ...),
        obligation=(obligation, ...),
        more_obligations=(list[obligation], ...),
    )
    return yielded | _NoObligation | _RaisedOpenQuestion


def slot_model(ids: list[str], scoped: bool, texts: dict[str, str]) -> type:
    fields = {}
    for requirement_id in ids:
        field = requirement_id.replace("-", "_")
        if scoped:
            fields[field] = (quote_scoped(requirement_id, sentences(texts[requirement_id])), ...)
        else:
            fields[field] = (_Yielded | _NoObligation | _RaisedOpenQuestion, ...)
    fields["open_questions"] = (list[_OpenQuestion], ...)
    return create_model("_Decomposition", __base__=StrictResponseModel, **fields)


def main(path: str) -> None:
    parsed = parse_task_file(open(path).read())
    registry = build_registry(parsed)
    texts = {ref.id: ref.span.text for ref in registry}
    ids = [ref.id for ref in registry]
    print(f"{path}: {len(registry)} requirements\n")

    print(f"{'batch':>6}  {'today':>8} {'slots':>8} {'slots+quote':>12} {'single+quote':>13}")
    for size in (1, 3, 8):
        batch = ids[:size]
        today = rendered(constrain(_Decomposition, {"requirement_id": batch}))
        slots = rendered(slot_model(batch, False, texts))
        scoped = rendered(slot_model(batch, True, texts))
        single = rendered(slot_model(batch[:1], True, texts))
        print(f"{size:>6}  {today:>8} {slots:>8} {scoped:>12} {single:>13}")

    print("\nquote-enum size per requirement (sentences offered):")
    for ref in registry[:6]:
        print(f"  {ref.id:15} {len(sentences(ref.span.text)):>2}  "
              f"{len(json.dumps(sentences(ref.span.text))):>5} bytes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dogfood-logs/313-gate1-run1/current-task.md")
