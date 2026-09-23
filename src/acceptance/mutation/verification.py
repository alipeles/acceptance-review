"""Checks that an edit really makes its named defect true, before its result counts.

The tier gate in `attempt.py` lets an observed kill or survival reach
`DEFECT_KILLED` only once its edit is verified. This is the verification: one
model call per observed edit, asking whether the code had the defect's expected
behaviour before the edit and its defective behaviour after it. Anything else is
refused, including an edit to code that already had the defective behaviour.

Before that call, an edit whose code is identical once comments and whitespace
are removed is refused with no model call, since no answer could be in doubt.
**In a pipeline run nothing reaches that early return any more** —
`validity.py` applies the same comparison to every candidate, whether or not
verification is on, so such an edit is already `not_mutable`. It is kept because
`verify_edits` is callable on an edit that did not come through the gates, and
it calls `validity.comparable` rather than its own copy so the two cannot
disagree.

**#335 split this into two model calls and the split was removed again**, on the
human's decision of 2026-09-23. The first call asked whether the edit changed
behaviour at all. Measured on audit v10 it refused **none** of the 52 edits, and
missed all four that the judging pass found to change no behaviour, one of which
it let through to be verified. It cost one model call per edit and changed no
outcome. `VerificationStep` survives it: the mechanical comparison still records
`BEHAVIOUR_CHANGE`, so a refusal for changing nothing stays distinguishable from
a refusal for changing the wrong thing.

**It reverses DR-171 Decision 3**, which ruled out a confirming model call. The
measurement that reversal rests on — what share of known-bad edits this catches,
and what share of known-good ones it wrongly rejects — is recorded in DR-171, and
the stage is off by default (`ExecutionSettings.verify_edits`) until it is
adopted on those numbers.

The call is not shown the tests or what they did: the question is whether the
edit makes the defect true, and knowing which tests failed would invite judging
the edit by its outcome.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from acceptance.change.context import RetrievalResult
from acceptance.concurrency import map_calls
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel as _Model
from acceptance.mutation.attempt import MutationAttempt, MutationDescriptor, VerificationStep
from acceptance.mutation.surrounding import contexts_for, render_contexts
from acceptance.mutation.validity import apply_span, comparable
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import Defect

__all__ = ["CONTEXT_LINES", "EditVerdict", "verify_attempts", "verify_edits"]

_MATCH_STAGE = "mutation verification: defect match"

#: Lines of unchanged code shown on each side of the edit. Enough to see the
#: enclosing function in most code, without shipping whole files per call.
CONTEXT_LINES = 30

_MATCH_PROMPT = """You check whether ONE edit to a codebase does what it was \
meant to do.

You are given a named defect, stated as two behaviours:
- EXPECTED: what the code must do.
- DEFECTIVE: what the code would do if the defect were present.

You are also given the code around one edit, BEFORE the edit and AFTER it.

Answer two questions about the code, each on its own evidence:

1. `before_does`: which behaviour does the code have BEFORE the edit?
2. `after_does`: which behaviour does the code have AFTER the edit?

Answer "expected" or "defective" when the code clearly does that behaviour. \
Answer "other" for `after_does` when the edit changes something, but not into \
the DEFECTIVE behaviour — for example it changes a different behaviour than the \
two sentences are about. Answer "cannot_tell" when the code shown is not enough \
to decide.

Judge the behaviour named in the two sentences, not whether the code still \
works. An edit that crashes the program, disables a whole feature, or breaks \
many unrelated things does not do the DEFECTIVE behaviour; it does something \
else. Answer "other" for that as well, and say so in `reason`.

Be strict. Do not give the edit the benefit of the doubt. In `reason`, one or \
two sentences naming the lines that decided each answer."""


class _Verification(StrictResponseModel):
    before_does: Literal["expected", "defective", "cannot_tell"]
    after_does: Literal["expected", "defective", "other", "cannot_tell"]
    reason: str


class EditVerdict(_Model):
    """What verification concluded about one edit.

    `refused_by` names what refused it — the mechanical comparison or the model
    call — and is empty for a verified edit. `before_does` and `after_does` are
    empty when the comparison refused the edit before any call was made.
    """

    verified: bool
    refused_by: VerificationStep | None = None
    before_does: str = ""
    after_does: str = ""
    reason: str


def verify_edits(
    items: Sequence[tuple[Defect, MutationDescriptor, str]],
    client: ModelClient,
    surrounding: RetrievalResult | None = None,
) -> list[EditVerdict]:
    """One verdict per `(defect, edit, source of the edited file)`, in input order.

    With `surrounding`, each call is also shown the enclosing definitions and
    call sites the edit falls in, as the edit-building call is (`surrounding.py`).

    Edits are checked concurrently and returned in input order, so two runs over
    the same input record the same thing (`concurrency.py`, rule 2).
    """
    return map_calls(list(items), lambda item: _ask(item[0], item[1], item[2], client, surrounding))


def verify_attempts(
    attempts: Sequence[MutationAttempt],
    defects: Sequence[Defect],
    sources: dict[str, str],
    client: ModelClient,
    surrounding: RetrievalResult | None = None,
) -> list[MutationAttempt]:
    """`attempts` with every observed one verified or not.

    Only an observed attempt — the tests were run against its edit — is asked
    about. Everything else is returned as it was: it has no result to count.
    """
    by_id = {defect.id: defect for defect in defects}
    asking = [
        attempt
        for attempt in attempts
        if attempt.observed
        and attempt.descriptor is not None
        and attempt.defect_id in by_id
        and attempt.descriptor.path in sources
    ]
    verdicts = verify_edits(
        [(by_id[a.defect_id], a.descriptor, sources[a.descriptor.path]) for a in asking],
        client,
        surrounding,
    )
    decided = {
        attempt.defect_id: verdict for attempt, verdict in zip(asking, verdicts, strict=True)
    }
    return [
        attempt.model_copy(
            update={
                "verified": decided[attempt.defect_id].verified,
                "refused_by": decided[attempt.defect_id].refused_by,
                "verification_reason": _explain(decided[attempt.defect_id]),
            }
        )
        if attempt.defect_id in decided
        else attempt
        for attempt in attempts
    ]


def _ask(
    defect: Defect,
    descriptor: MutationDescriptor,
    source: str,
    client: ModelClient,
    surrounding: RetrievalResult | None = None,
) -> EditVerdict:
    after = apply_span(source, descriptor)
    if comparable(descriptor.path, source) == comparable(descriptor.path, after):
        return EditVerdict(
            verified=False,
            refused_by=VerificationStep.BEHAVIOUR_CHANGE,
            reason="the edit changes only comments or whitespace",
        )
    spans = [(descriptor.path, descriptor.start_line, descriptor.end_line)]
    # Shows the code BEFORE the edit, like the edit-building call saw it.
    context = render_contexts(contexts_for(spans, surrounding))
    partition_key = partition([defect], 1, key=lambda d: d.id)[0].request_partition()

    match = client.complete(
        _messages(
            _MATCH_PROMPT,
            f"{_defect_block(defect)}\n\n{_code(descriptor, source, after)}",
            context,
        ),
        _Verification,
        partition_key,
        parse_as=_Verification,
        stage=_MATCH_STAGE,
    )
    verified = match.before_does == "expected" and match.after_does == "defective"
    return EditVerdict(
        verified=verified,
        refused_by=None if verified else VerificationStep.DEFECT_MATCH,
        before_does=match.before_does,
        after_does=match.after_does,
        reason=match.reason.strip(),
    )


def _messages(prompt: str, subject: str, context: str) -> list[dict]:
    if context:
        subject = f"{subject}\n\n{context}"
    return assemble([Block(BlockKind.INSTRUCTIONS, prompt), Block(BlockKind.SUBJECT, subject)])


def _explain(verdict: EditVerdict) -> str:
    if verdict.refused_by is VerificationStep.BEHAVIOUR_CHANGE:
        return (
            f"verification refused the edit without asking a model: the edit does not "
            f"change the code's behaviour. {verdict.reason}"
        ).strip()
    outcome = "verified" if verdict.verified else "refused"
    return (
        f"verification {outcome}: before the edit the code does {verdict.before_does}, "
        f"after it {verdict.after_does}. {verdict.reason}"
    ).strip()


def _defect_block(defect: Defect) -> str:
    expected = defect.expected_behavior or "the opposite of the description below"
    defective = defect.defective_behavior or defect.description
    return "\n".join(
        [
            "## The defect",
            f"description: {defect.description}",
            f"EXPECTED: {expected}",
            f"DEFECTIVE: {defective}",
        ]
    )


def _code(descriptor: MutationDescriptor, before: str, after: str) -> str:
    """The code around the edit, before and after it."""
    new_end = descriptor.start_line + len(descriptor.replacement.splitlines()) - 1
    return "\n".join(
        [
            f"## BEFORE the edit — {descriptor.path}",
            _window(before.splitlines(), descriptor.start_line, descriptor.end_line),
            "",
            f"## AFTER the edit — {descriptor.path}",
            _window(after.splitlines(), descriptor.start_line, max(new_end, descriptor.start_line)),
        ]
    )


def _window(lines: list[str], start: int, end: int) -> str:
    first = max(1, start - CONTEXT_LINES)
    last = min(len(lines), end + CONTEXT_LINES)
    width = len(str(last))
    return "\n".join(
        f"{number:>{width}} | {lines[number - 1]}" for number in range(first, last + 1)
    )
