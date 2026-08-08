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

from acceptance.config import DEFAULT_DECOMPOSE_BATCH_SIZE
from acceptance.llm import ModelClient, SchemaValidationError, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.partition import partition
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
from acceptance.supplied_ids import (
    UnusableAnswer,
    UnusableAnswerLog,
    constrain,
    scan,
)

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

Every obligation belongs to exactly ONE requirement. Account for each
requirement on its own: split it into several obligations, or decline it with
`no_obligation`, but never name one obligation in two requirements'
dispositions.

When two requirements state the same thing — commonly one bullet under
Constraints and another under Completion expectations — emit an obligation for
EACH of them. Two obligations saying nearly the same thing is the correct
output here; a later pass merges them. Do not try to save the duplicate by
attaching one obligation to both, because the requirement whose own content
does not survive that merge is lost silently, and nothing downstream can tell."""


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


def _user_prompt(registry: list[RequirementRef], answer_for: set[str]) -> str:
    """The identified requirements, as typed fields — all of them, every call.

    Deliberately NOT `parsed.source`. The pipeline runs `parse_task_file`, which
    computes typed spans for the behavior, constraints, scope exclusions and
    completion expectations — and the previous version of this function threw
    all of that away and pasted the raw markdown back for the model to re-derive.
    That is the CLAUDE.md structured-interchange invariant: markdown is an input
    format and a rendering format, never an interchange format.

    It is also what makes the disposition list enforceable. Asking for "one entry
    per requirement" only means something if the code and the model agree on what
    the requirements ARE, and that agreement is this list.

    **The batch scopes which requirements this call must answer for; it does not
    scope what the call may read** (#204). The whole registry is the task file in
    its structured form, so every call sees all of it. #178 is a failure to
    reconcile across sections, and a call shown only its own bullets cannot
    notice that a later section settles a term an earlier one leaves open — it
    would trade one silent loss for another.
    """
    lines = [
        "The complete set of requirements in this task file, for context:",
        "",
    ]
    for requirement in registry:
        marker = "ANSWER FOR THIS" if requirement.id in answer_for else "context only"
        lines.append(
            f"[{requirement.id}] ({requirement.section.value}) [{marker}] {requirement.text}"
        )
    lines.extend(
        [
            "",
            "Return exactly one disposition for each of these requirement ids, and "
            "for no others:",
            "",
            ", ".join(sorted(answer_for)),
            "",
            "The rest are shown so you can read the mandate as a whole. Do not "
            "dispose of them and do not derive obligations for them; another call "
            "answers for those.",
        ]
    )
    return "\n".join(lines)


def _importance(value: str) -> str:
    return "critical" if value == "critical" else "normal"


def decompose(
    parsed: ParsedTaskFile,
    client: ModelClient,
    unusable_answers: UnusableAnswerLog | None = None,
    batch_size: int = DEFAULT_DECOMPOSE_BATCH_SIZE,
) -> Decomposition:
    """Decompose a parsed task into typed obligations, open questions, and the
    mapping from each identified requirement to what it produced.

    Takes a parsed task file and a client, and nothing else — no `ChangeSet`, no
    repository, no head revision (DR-202 decision 8).

    The requirements are partitioned across several calls (#204). One call over
    the whole registry sheds work the way DR-164 measured a stage later: an
    observed run over ~36 requirements produced no obligation for 9 of them,
    with a schema-valid response that nothing downstream could question. Every
    call still reads the whole task file; only the answering is split.
    """
    registry = build_registry(parsed)
    # No requirements, no calls. `partition` returns no batches for an empty
    # registry and the loop below simply does not run — spelled out because the
    # previous single-call shape issued one request regardless, asking the model
    # to decompose an empty requirement list. What came back could only be
    # invented, since the prompt carried no task content at all.
    #
    # This is how `tests/fixtures/archetypes/` behaves today: every task.md
    # there heads its mandate `# Task: <title>`, which is not the `task` heading
    # the parser recognises, so all thirteen produce an empty registry. Tracked
    # separately — it is a property of that corpus, not of this stage.

    seen_ids: set[str] = set()
    obligations: list[Obligation] = []
    open_questions: list[OpenQuestion] = []
    dispositions: list[_RequirementDisposition] = []
    # Keyed by REQUIREMENT, not merged into one model-id -> final-id map. Each
    # response mints its own obligation ids, so two batches can both return
    # `obligation-foo` meaning different things; `_unique` renames the second to
    # `obligation-foo-2`. A single shared map would then hold one entry for
    # `obligation-foo` — whichever batch wrote last — and resolve BOTH batches'
    # dispositions onto it. That is a requirement silently attached to an
    # obligation derived from another requirement: the exact mis-link this
    # change exists to make impossible, reintroduced in the merge.
    #
    # Every requirement belongs to exactly one batch, so keying by requirement
    # is unambiguous and each disposition resolves through its own call's map.
    obligation_final: dict[str, dict[str, str]] = {}
    question_final: dict[str, dict[str, str]] = {}

    for batch in partition(registry, batch_size, key=lambda requirement: requirement.id):
        batch_ids = [requirement.id for requirement in batch.items]
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(registry, set(batch_ids))},
        ]
        # Constrained to THIS batch's ids, not the whole registry: a disposition
        # for a requirement another call owns is unrepresentable under
        # constrained decoding, and caught locally otherwise (#163). Obligation
        # and question ids are minted by the same response, so there is nothing
        # to constrain them against; they are reconciled below.
        allowed = {"requirement_id": batch_ids}
        result = client.complete(
            messages,
            constrain(_Decomposition, allowed),
            batch.request_partition(),
            parse_as=_Decomposition,
            stage=_STAGE,
        )
        if unusable_answers is not None:
            unusable_answers.record(scan(result, allowed, _STAGE))

        batch_obligation_final: dict[str, str] = {}
        for item in result.obligations:
            final_id = _unique(item.id, seen_ids)
            batch_obligation_final.setdefault(item.id, final_id)
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

        batch_question_final: dict[str, str] = {}
        for item in result.open_questions:
            final_id = _unique(item.id, seen_ids)
            batch_question_final.setdefault(item.id, final_id)
            open_questions.append(
                OpenQuestion(
                    id=final_id,
                    question=item.question,
                    importance=_importance(item.importance),
                    source_spans=_spans(parsed.source, item.source_quote),
                )
            )

        kept = _batch_dispositions(
            result.requirement_dispositions,
            set(batch_ids),
            {requirement.id for requirement in registry},
            unusable_answers,
        )
        dispositions.extend(kept)
        for requirement_id in batch_ids:
            obligation_final[requirement_id] = batch_obligation_final
            question_final[requirement_id] = batch_question_final

    return Decomposition(
        obligations=obligations,
        open_questions=open_questions,
        requirement_map=_requirement_map(
            registry,
            dispositions,
            obligation_final,
            question_final,
            parsed.unclaimed,
        ),
    )


def _batch_dispositions(
    returned: list[_RequirementDisposition],
    batch_ids: set[str],
    registry_ids: set[str],
    unusable_answers: UnusableAnswerLog | None,
) -> list[_RequirementDisposition]:
    """One batch's usable dispositions, with the two rejections #204 requires.

    **A batch may only answer for its own requirements.** A disposition naming a
    requirement this call was not given is recorded and dropped rather than
    silently filtered — the requirement belongs to another batch, which answers
    for it, and letting this one through would make the merged result depend on
    which batch returned last.

    **Derivation performs no linking** (DR-204). A response naming one obligation
    in two requirements' dispositions has both dropped, not one arbitrarily
    kept. Choosing a winner is exactly the silent loss the rule exists to
    prevent: the losing requirement's content disappears into an obligation that
    does not state it, under a disposition count that still looks complete.

    Dropping leaves those requirements unaccounted for, and `_requirement_map`
    raises on that — deliberately. A response that does not account for the
    mandate is not a review with a gap in it; it is not a review. The
    `unusable_answer` record is the diagnosis, and the raise is the enforcement.
    """
    rejected: list[UnusableAnswer] = []
    usable: list[_RequirementDisposition] = []

    for entry in returned:
        # An id outside the registry ENTIRELY is passed through, not filtered
        # here: it is a malformed response rather than a batch overstepping, and
        # `_requirement_map` already refuses it by name. Filtering it here would
        # convert a loud, specific rejection into a vague "did not account for"
        # about some other requirement.
        if entry.requirement_id in registry_ids and entry.requirement_id not in batch_ids:
            rejected.append(
                UnusableAnswer(
                    stage=_STAGE,
                    field="requirement_id",
                    returned_id=entry.requirement_id,
                    reason="disposed a requirement this call was not asked to answer for",
                )
            )
            continue
        usable.append(entry)

    # Which obligation ids more than one requirement claimed, within this one
    # response. Cross-batch linking needs no check: ids originate per call, so it
    # is not expressible.
    claims: dict[str, list[str]] = {}
    for entry in usable:
        if isinstance(entry, _Yielded):
            for obligation_id in entry.ids():
                claims.setdefault(obligation_id, []).append(entry.requirement_id)

    linked = {
        obligation_id: claimants
        for obligation_id, claimants in claims.items()
        if len(claimants) > 1
    }
    for obligation_id, claimants in sorted(linked.items()):
        rejected.append(
            UnusableAnswer(
                stage=_STAGE,
                field="obligation_id",
                returned_id=obligation_id,
                reason=(
                    "one obligation was named by "
                    f"{len(claimants)} requirements ({', '.join(sorted(claimants))}); "
                    "derivation performs no linking"
                ),
            )
        )

    if linked:
        dropped = {
            requirement_id for claimants in linked.values() for requirement_id in claimants
        }
        usable = [entry for entry in usable if entry.requirement_id not in dropped]

    if rejected and unusable_answers is not None:
        unusable_answers.record(rejected)
    return usable


def _requirement_map(
    registry: list[RequirementRef],
    returned: list[_RequirementDisposition],
    obligation_final: dict[str, dict[str, str]],
    question_final: dict[str, dict[str, str]],
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
            obligation_ids = _resolve(entry.ids(), obligation_final.get(requirement.id, {}))
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

        open_question_ids = _resolve(entry.ids(), question_final.get(requirement.id, {}))
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
