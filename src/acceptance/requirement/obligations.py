"""Obligation decomposition (M1.2/M1.3, §7.3/§9.1).

Converts a parsed task file into discrete, typed obligations plus the material
ambiguities that need user judgment. Decomposition is a semantic judgment, so
it is a schema-constrained model call through the M0.4 harness — recorded for
replay, never a live call in tests.

Each obligation and open question is linked to a `TextSpan` in the task (the
model returns an exact `source_quote` which we locate in the source), so every
output traces back to the requirement text it came from (CLAUDE.md invariant).
Material ambiguities are surfaced as `OpenQuestion`s rather than invented
obligations — uncertainty is a first-class, expected result (M1.3).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from acceptance.llm import ModelClient
from acceptance.model_base import PersistableModel
from acceptance.requirement.task_file import ParsedTaskFile
from acceptance.review_state import Obligation, ObligationType, OpenQuestion
from acceptance.source_ref import find_span

_SYSTEM_PROMPT = """\
You decompose a software task into discrete, typed acceptance obligations and
the ambiguities that need human judgment.

For each obligation: a short stable `id` slug (kebab-case, unique); a
`description`; a `type` from the fixed set (functional, boundary,
error_handling, invariant, regression, compatibility,
explanation_observability, docs_config, human_review); `importance` (critical
or normal); `explicit` (true if directly stated in the task, false if
reasonably inferred); an `observable_behavior`; and `source_quote`, an EXACT
substring of the task text this obligation derives from.

Emit an inferred obligation (explicit=false) only when the inference is
reasonable and low-risk. When a requirement is materially underspecified — you
would have to guess a qualifier, value, or behavior to proceed — do NOT invent
an obligation for it. Instead return an `open_question` with a stable `id`, the
`question` to put to the user, an `importance`, and a `source_quote` for the
ambiguous text.

Do not merge distinct requirements. Prefer the smallest faithful set."""


class _DecomposedObligation(BaseModel):
    id: str
    description: str
    type: ObligationType
    importance: str
    explicit: bool
    observable_behavior: str
    source_quote: str


class _OpenQuestion(BaseModel):
    id: str
    question: str
    importance: str
    source_quote: str


class _Decomposition(BaseModel):
    obligations: list[_DecomposedObligation] = Field(default_factory=list)
    open_questions: list[_OpenQuestion] = Field(default_factory=list)


class Decomposition(PersistableModel):
    """The result of decomposing a task: typed obligations plus the open
    questions a good reviewer would raise rather than resolve."""

    obligations: list[Obligation] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)


def _user_prompt(parsed: ParsedTaskFile) -> str:
    return f"Task file:\n\n{parsed.source}"


def _importance(value: str) -> str:
    return "critical" if value == "critical" else "normal"


def decompose(parsed: ParsedTaskFile, client: ModelClient) -> Decomposition:
    """Decompose a parsed task into typed obligations and open questions."""
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _user_prompt(parsed)},
    ]
    result = client.complete(messages, _Decomposition)

    seen_ids: set[str] = set()
    obligations = [
        Obligation(
            id=_unique(item.id, seen_ids),
            description=item.description,
            type=item.type,
            importance=_importance(item.importance),
            explicit=item.explicit,
            observable_behavior=item.observable_behavior,
            source_spans=_spans(parsed.source, item.source_quote),
        )
        for item in result.obligations
    ]
    open_questions = [
        OpenQuestion(
            id=_unique(item.id, seen_ids),
            question=item.question,
            importance=_importance(item.importance),
            source_spans=_spans(parsed.source, item.source_quote),
        )
        for item in result.open_questions
    ]
    return Decomposition(obligations=obligations, open_questions=open_questions)


def _spans(source: str, quote: str) -> list:
    span = find_span(source, quote)
    return [span] if span is not None else []


def _unique(candidate: str, seen: set[str]) -> str:
    """Keep ids unique and deterministic across obligations and open questions."""
    unique_id = candidate
    suffix = 2
    while unique_id in seen:
        unique_id = f"{candidate}-{suffix}"
        suffix += 1
    seen.add(unique_id)
    return unique_id
