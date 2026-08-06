"""Obligation decomposition (M1.2/M1.3 and M1.2.r1, §7.3/§9.1).

Converts a parsed task file into discrete, typed obligations plus the material
ambiguities that need user judgment. Decomposition is a semantic judgment, so
it is a schema-constrained model call through the M0.4 harness — recorded for
replay, never a live call in tests.

Each obligation and open question is linked to a `TextSpan` in the task (the
model returns an exact `source_quote` which we locate in the source), so every
output traces back to the requirement text it came from (CLAUDE.md invariant).
Material ambiguities are surfaced as `OpenQuestion`s rather than invented
obligations — uncertainty is a first-class, expected result (M1.3).

**What decomposition returns is a mapping, not a list** (M1.2.r1, DR-202). The
call is asked for one disposition per identified requirement, so a requirement
that produced nothing is a recorded fact rather than an absence. A flat
obligation list made a response covering 20 of 29 requirements exactly as
well-formed as one covering all 29, which is how #195's Gate 1 lost 4 of 15
Completion expectations and 5 of 8 Scope exclusions without the review saying so.

**A response that does not account for the mandate is rejected, not recorded**
(M1.2.r2). Each disposition is one of three shapes, each structurally carrying
what its name claims, and reconciliation raises on anything else: a missing
requirement, a duplicate, an id outside the registry, or a claim naming outputs
the response never produced. `M1.2.r1` recorded those as a fourth disposition
instead, which let a malformed response reach a verdict as a soft finding.

**The decomposer is code-blind** (DR-202 decision 8): it takes a parsed task
file and a client, and never a `ChangeSet`, a repository path or a head
revision. Decomposing the mandate in light of the delivered implementation makes
a missing obligation and a missing implementation correlated errors, which
destroys the one thing the review exists to detect. Pinned by a test.
"""

from __future__ import annotations

from typing import Literal, Union

from pydantic import Field

from acceptance.llm import ModelClient, SchemaValidationError, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import ParsedTaskFile
from acceptance.review_state import (
    Disposition,
    Obligation,
    ObligationType,
    OpenQuestion,
    RequirementDisposition,
    RequirementMap,
    RequirementRef,
)
from acceptance.source_ref import find_span
from acceptance.supplied_ids import UnusableAnswerLog, constrain, scan

_STAGE = "decompose"

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

State every obligation as a POSITIVE invariant — the property the delivered
code must HOLD — never as a prohibition. A requirement phrased as "don't ...",
"never ...", or "leave X unchanged" describes a property to PRESERVE; restate
it as that property:
- "Don't change the existing checkout behavior" -> "Preserve the existing
  checkout behavior."
- "Don't add new dependencies" -> "Keep the dependency set unchanged."
- "Don't slow down the report" -> "Keep the report's runtime within its
  current bound."
A prohibition and the invariant it protects are the same obligation; emit the
positive form, because it states what must be TRUE rather than what must be
absent — an obligation that only says what must be absent can never be shown
addressed by looking at what the diff contains.

Granularity — isolate distinct computations, keep cohesive behaviors whole:

- Isolate a sub-clause that defines a DISTINCT COMPUTATION or derived value — a
  formula or calculation with its own logic, embedded via "where ...",
  "using ...", "based on ..." — that could be computed wrongly on its own,
  independently of the step that uses it. E.g. "charge for the hours worked at
  the overtime rate, where the overtime rate is 1.5x base pay" is TWO
  obligations: charging for the hours, and the overtime-rate formula (the rate
  can be wrong independently of the multiplication). Do not fold such a
  computation into its host clause.

- Keep as ONE obligation a single cohesive behavior — a parse, a
  lookup/mapping, a formatting or display rule — even when it spans several
  inputs, fields, or cases. "Parse the token into its type and value" is one
  obligation, not a separate 'read the token' and 'classify it'; "render each
  column right-aligned" is one display rule, not one per column.

The test: is the sub-clause a SEPARATE calculation that could be individually
wrong, or one behavior applied across cases? Separate the former; keep the
latter whole. Prefer the smallest set that still isolates every distinct
computation.

ACCOUNTING FOR EVERY REQUIREMENT

You are given the task file's requirements as an identified list. Return
`requirement_dispositions` containing EXACTLY ONE entry for EVERY requirement id
you were given — including the ones you find unremarkable. A requirement you
omit is not treated as unimportant; it is recorded as one you failed to read.

Each disposition is one of:

- `yielded` — the requirement produced one or more obligations. List their ids
  in `obligation_ids`. This is the normal case and should be the large majority.
- `open_question` — the requirement is materially underspecified, so you raised
  a question instead of inventing an obligation. List the question ids in
  `open_question_ids`.
- `no_obligation` — the requirement genuinely imposes nothing checkable. Give
  the `reason`. This is rare and narrow: a section marker such as
  "Implementation" or "Deliverable", standing alone with no requirement under
  it. It is NOT the answer for a requirement that is merely hard to phrase.

REFERENCES YOU CANNOT RESOLVE

A requirement will often cite something you were not given — an issue number, a
ticket, a document, a person, a symbol from a file you cannot see. This is
NORMAL and it does NOT weaken the requirement. **Decompose it from the text you
DO have.** Never dispose of a requirement as `no_obligation` on the grounds that
it points at something outside your view; that is a fact about your inputs, not
about the mandate.

    "Assigning obligation types in a separate pass, which is #205."

states a requirement — obligation types are not assigned in this change —
whether or not you know what #205 is. The clause "which is #205" is an
attribution, not the content. Read past it and decompose the rest.

The test is whether the sentence constrains the delivered change for a reader
who also cannot resolve the reference. Almost always it does. If the unresolved
reference genuinely leaves you unable to tell WHAT is required — not merely
unable to see the related material — raise an `open_question` instead. Do not
answer with `no_obligation`.

In particular, a **scope exclusion is a requirement and yields an obligation**.
"Don't do X" is the invariant "X is preserved unchanged", which is exactly the
positive restatement described above, and it is checkable — the delivered change
either touched X or it did not. Do not dispose of a scope exclusion as
`no_obligation` because it is phrased as a prohibition; restate it and yield.

One obligation may serve SEVERAL requirements. When two requirements state the
same thing — commonly one bullet under Constraints and another under Completion
expectations — emit ONE obligation and name it in BOTH dispositions. Never emit
two near-identical obligations so that each requirement has its own copy."""


# Empty arrays are returned explicitly (StrictResponseModel: no defaults).
class _DecomposedObligation(StrictResponseModel):
    id: str
    description: str
    type: ObligationType
    importance: str
    explicit: bool
    observable_behavior: str
    source_quote: str


class _OpenQuestion(StrictResponseModel):
    id: str
    question: str
    importance: str
    source_quote: str


class _Yielded(StrictResponseModel):
    """Obligations were derived. At least one, structurally."""

    requirement_id: str
    disposition: Literal["yielded"]
    # Split rather than `list[str]` with a minimum, because a minimum cannot be
    # expressed on the wire: OpenAI strict mode rejects `minItems`. One required
    # field plus the rest makes "at least one" a property of the SHAPE, so the
    # empty case is unrepresentable in the schema the model is given rather than
    # merely rejected after it answers.
    obligation_id: str
    more_obligation_ids: list[str]

    def ids(self) -> list[str]:
        return [self.obligation_id, *self.more_obligation_ids]


class _NoObligation(StrictResponseModel):
    """Deliberately yields none. The reason is the disposition's whole content,
    so the shape has nowhere to put obligations."""

    requirement_id: str
    disposition: Literal["no_obligation"]
    reason: str


class _RaisedOpenQuestion(StrictResponseModel):
    """An open question prevents answering. At least one, structurally."""

    requirement_id: str
    disposition: Literal["open_question"]
    open_question_id: str
    more_open_question_ids: list[str]

    def ids(self) -> list[str]:
        return [self.open_question_id, *self.more_open_question_ids]


# A plain `Union`, deliberately not `Field(discriminator=...)`: pydantic renders
# a tagged union as `oneOf` + `discriminator`, and strict mode accepts neither,
# while `inline_schema_refs` would leave the discriminator mapping pointing at
# `$defs` it had just inlined. A plain union renders `anyOf`, which strict mode
# does accept, and the `Literal` tags still make the match unambiguous.
_RequirementDisposition = Union[_Yielded, _NoObligation, _RaisedOpenQuestion]


class _Decomposition(StrictResponseModel):
    obligations: list[_DecomposedObligation]
    open_questions: list[_OpenQuestion]
    requirement_dispositions: list[_RequirementDisposition]


class Decomposition(PersistableModel):
    """The result of decomposing a task: typed obligations, the open questions a
    good reviewer would raise rather than resolve, and the mapping back to the
    requirements each came from."""

    obligations: list[Obligation] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    requirement_map: RequirementMap = Field(default_factory=RequirementMap)


def _user_prompt(registry: list[RequirementRef]) -> str:
    """The identified requirements, as typed fields.

    Deliberately NOT `parsed.source`. The pipeline runs `parse_task_file`, which
    computes typed spans for the behavior, constraints, scope exclusions and
    completion expectations — and the previous version of this function threw
    all of that away and pasted the raw markdown back for the model to re-derive.
    That is the CLAUDE.md structured-interchange invariant: markdown is an input
    format and a rendering format, never an interchange format.

    It is also what makes the disposition list enforceable. Asking for "one entry
    per requirement" only means something if the code and the model agree on what
    the requirements ARE, and that agreement is this list.
    """
    lines = [
        "Requirements, each with the id you must account for it under:",
        "",
    ]
    for requirement in registry:
        lines.append(f"[{requirement.id}] ({requirement.section.value}) {requirement.text}")
    return "\n".join(lines)


def _importance(value: str) -> str:
    return "critical" if value == "critical" else "normal"


def decompose(
    parsed: ParsedTaskFile,
    client: ModelClient,
    unusable_answers: UnusableAnswerLog | None = None,
) -> Decomposition:
    """Decompose a parsed task into typed obligations, open questions, and the
    mapping from each identified requirement to what it produced.

    Takes a parsed task file and a client, and nothing else — no `ChangeSet`, no
    repository, no head revision (DR-202 decision 8).
    """
    registry = build_registry(parsed)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _user_prompt(registry)},
    ]
    # Requirement ids are ours, so a foreign one is unrepresentable under
    # constrained decoding and detected locally otherwise (#163). Obligation and
    # question ids are minted by this same response, so there is nothing to
    # constrain them against; they are reconciled below instead.
    allowed = {"requirement_id": [requirement.id for requirement in registry]}
    result = client.complete(
        messages,
        constrain(_Decomposition, allowed),
        parse_as=_Decomposition,
    )
    if unusable_answers is not None:
        unusable_answers.record(scan(result, allowed, _STAGE))

    seen_ids: set[str] = set()
    obligations: list[Obligation] = []
    # The model's own id for each output, mapped to the id it ended up with:
    # `_unique` may rename a collision, and a disposition naming the original
    # would otherwise dangle. First claimant wins, which is the only stable
    # reading when the model emits the same id twice.
    obligation_final: dict[str, str] = {}
    for item in result.obligations:
        final_id = _unique(item.id, seen_ids)
        obligation_final.setdefault(item.id, final_id)
        obligations.append(
            Obligation(
                id=final_id,
                description=item.description,
                type=item.type,
                importance=_importance(item.importance),
                explicit=item.explicit,
                observable_behavior=item.observable_behavior,
                source_spans=_spans(parsed.source, item.source_quote),
            )
        )

    open_questions: list[OpenQuestion] = []
    question_final: dict[str, str] = {}
    for item in result.open_questions:
        final_id = _unique(item.id, seen_ids)
        question_final.setdefault(item.id, final_id)
        open_questions.append(
            OpenQuestion(
                id=final_id,
                question=item.question,
                importance=_importance(item.importance),
                source_spans=_spans(parsed.source, item.source_quote),
            )
        )

    return Decomposition(
        obligations=obligations,
        open_questions=open_questions,
        requirement_map=_requirement_map(
            registry,
            result.requirement_dispositions,
            obligation_final,
            question_final,
            parsed.unclaimed,
        ),
    )


def _requirement_map(
    registry: list[RequirementRef],
    returned: list[_RequirementDisposition],
    obligation_final: dict[str, str],
    question_final: dict[str, str],
    unread: list,
) -> RequirementMap:
    """Reconcile the returned dispositions against the registry.

    The registry is derived deterministically from the parse and this loop walks
    it, so **dropping a requirement is not a reachable outcome** — the worst a
    model can do is answer badly. That is why there is no fourth disposition
    here. `M1.2.r1` added one, `UNDISPOSED`, for a requirement the response
    failed to account for, and it turned two kinds of malformed response into a
    soft finding that flowed on to a verdict. A response that does not account
    for the mandate is not a review with a gap in it; it is not a review.

    So every disagreement between the registry and the response raises. What
    survives is a map in which every requirement carries one of decision 3's
    three dispositions, each holding what its name claims.
    """
    by_requirement: dict[str, _RequirementDisposition] = {}
    for entry in returned:
        if entry.requirement_id in by_requirement:
            raise SchemaValidationError(
                f"requirement '{entry.requirement_id}' was disposed more than once"
            )
        by_requirement[entry.requirement_id] = entry

    known = {requirement.id for requirement in registry}
    unknown = sorted(set(by_requirement) - known)
    if unknown:
        raise SchemaValidationError(
            f"response disposed requirement ids not in the registry: {', '.join(unknown)}"
        )
    missing = [requirement.id for requirement in registry if requirement.id not in by_requirement]
    if missing:
        raise SchemaValidationError(
            f"response did not account for {len(missing)} of {len(registry)} "
            f"requirements: {', '.join(missing)}"
        )

    dispositions: list[RequirementDisposition] = []
    for requirement in registry:
        entry = by_requirement[requirement.id]

        if isinstance(entry, _NoObligation):
            dispositions.append(
                RequirementDisposition(
                    requirement_id=requirement.id,
                    disposition=Disposition.NO_OBLIGATION,
                    reason=entry.reason,
                )
            )
            continue

        # Ids the response invented are still dropped — a disposition may only
        # name outputs the same response produced. But dropping them all is not
        # a survivable state: it leaves a claim that obligations exist with none
        # to point at, which is the contradiction this change exists to remove.
        if isinstance(entry, _Yielded):
            obligation_ids = _resolve(entry.ids(), obligation_final)
            if not obligation_ids:
                raise SchemaValidationError(
                    f"requirement '{requirement.id}' was disposed 'yielded' naming "
                    f"{len(entry.ids())} obligation id(s), none of which the response produced"
                )
            dispositions.append(
                RequirementDisposition(
                    requirement_id=requirement.id,
                    disposition=Disposition.YIELDED,
                    obligation_ids=obligation_ids,
                )
            )
            continue

        open_question_ids = _resolve(entry.ids(), question_final)
        if not open_question_ids:
            raise SchemaValidationError(
                f"requirement '{requirement.id}' was disposed 'open_question' naming "
                f"{len(entry.ids())} question id(s), none of which the response produced"
            )
        dispositions.append(
            RequirementDisposition(
                requirement_id=requirement.id,
                disposition=Disposition.OPEN_QUESTION,
                open_question_ids=open_question_ids,
            )
        )

    return RequirementMap(
        requirements=registry, dispositions=dispositions, unread_source=unread
    )


def _resolve(ids: list[str], final: dict[str, str]) -> list[str]:
    """Returned output ids mapped to the ids those outputs actually carry,
    de-duplicated, in first-seen order (byte-identical reruns depend on it)."""
    resolved: dict[str, None] = {}
    for value in ids:
        actual = final.get(value)
        if actual is not None:
            resolved.setdefault(actual, None)
    return list(resolved)


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
