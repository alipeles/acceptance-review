"""Obligation decomposition (M1.2, §7.3/§9.1).

Converts a parsed task file into discrete, typed obligations. Decomposition is
a semantic judgment, so it is a schema-constrained model call through the M0.4
harness — recorded for replay, never a live call in tests. The model returns
each obligation with a `source_quote` (exact text from the task); we locate
that quote in the source to attach a `TextSpan`, so every obligation traces
back to the requirement text it came from (CLAUDE.md invariant).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from acceptance.llm import ModelClient
from acceptance.requirement.task_file import ParsedTaskFile
from acceptance.review_state import Obligation, ObligationType
from acceptance.source_ref import find_span

_SYSTEM_PROMPT = """\
You decompose a software task into discrete, typed acceptance obligations.

Return one obligation per distinct, independently checkable requirement. For
each: a short stable `id` slug (kebab-case, unique); a `description`; a `type`
from the fixed set (functional, boundary, error_handling, invariant,
regression, compatibility, explanation_observability, docs_config,
human_review); `importance` (critical or normal); `explicit` (true if directly
stated in the task, false if reasonably inferred); an `observable_behavior`
describing how the obligation is observed; and `source_quote`, an EXACT
substring of the task text this obligation derives from.

Do not invent obligations the task does not support. Do not merge distinct
requirements. Prefer the smallest faithful set."""


class _DecomposedObligation(BaseModel):
    id: str
    description: str
    type: ObligationType
    importance: str
    explicit: bool
    observable_behavior: str
    source_quote: str


class _Decomposition(BaseModel):
    obligations: list[_DecomposedObligation] = Field(default_factory=list)


def _user_prompt(parsed: ParsedTaskFile) -> str:
    return f"Task file:\n\n{parsed.source}"


def decompose(parsed: ParsedTaskFile, client: ModelClient) -> list[Obligation]:
    """Decompose a parsed task into typed obligations, linked to source spans."""
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _user_prompt(parsed)},
    ]
    decomposition = client.complete(messages, _Decomposition)

    obligations: list[Obligation] = []
    seen_ids: set[str] = set()
    for item in decomposition.obligations:
        obligation_id = _unique(item.id, seen_ids)
        span = find_span(parsed.source, item.source_quote)
        obligations.append(
            Obligation(
                id=obligation_id,
                description=item.description,
                type=item.type,
                importance="critical" if item.importance == "critical" else "normal",
                explicit=item.explicit,
                observable_behavior=item.observable_behavior,
                source_spans=[span] if span is not None else [],
            )
        )
    return obligations


def _unique(candidate: str, seen: set[str]) -> str:
    """Keep obligation ids unique and deterministic (suffix on collision)."""
    obligation_id = candidate
    suffix = 2
    while obligation_id in seen:
        obligation_id = f"{candidate}-{suffix}"
        suffix += 1
    seen.add(obligation_id)
    return obligation_id
