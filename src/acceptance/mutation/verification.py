"""Checks that an edit really makes its named defect true, before its result counts.

The tier gate in `attempt.py` lets an observed kill or survival reach
`DEFECT_KILLED` only once its edit is verified. This is the verification: one
model call per observed edit, asked two questions about the code — which of the
defect's two behaviours it has BEFORE the edit, and which AFTER. The edit is
verified only when the answers are "expected" and then "defective".

**It reverses DR-171 Decision 3**, which ruled out a confirming model call. The
measurement that reversal rests on — what share of known-bad edits this catches,
and what share of known-good ones it wrongly rejects — is recorded in DR-171, and
the stage is off by default (`ExecutionSettings.verify_edits`) until it is
adopted on those numbers.

The call is shown the defect, and the code around the edit before and after it.
It is **not** shown the tests or what they did: the question is whether the edit
makes the defect true, and knowing which tests failed would invite judging the
edit by its outcome.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from acceptance.concurrency import map_calls
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel as _Model
from acceptance.mutation.attempt import MutationAttempt, MutationDescriptor
from acceptance.mutation.validity import apply_span
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import Defect

__all__ = ["CONTEXT_LINES", "EditVerdict", "verify_attempts", "verify_edits"]

_STAGE = "mutation verification"

#: Lines of unchanged code shown on each side of the edit. Enough to see the
#: enclosing function in most code, without shipping whole files per call.
CONTEXT_LINES = 30

_SYSTEM_PROMPT = """You check whether ONE edit to a codebase does what it was \
meant to do.

You are given a named defect, stated as two behaviours:
- EXPECTED: what the code must do.
- DEFECTIVE: what the code would do if the defect were present.

You are also given the code around one edit, BEFORE the edit and AFTER it.

Answer two questions about the code, each on its own evidence:

1. `before_does`: which behaviour does the code have BEFORE the edit?
2. `after_does`: which behaviour does the code have AFTER the edit?

Answer "expected" or "defective" when the code clearly does that behaviour. \
Answer "unchanged" for `after_does` when the edit does not change the behaviour \
the two sentences are about — for example it reformats, renames, reorders, \
adds a condition that is always true, or changes something else entirely. \
Answer "cannot_tell" when the code shown is not enough to decide.

Judge the behaviour named in the two sentences, not whether the code still \
works. An edit that crashes the program, disables a whole feature, or breaks \
many unrelated things does not do the DEFECTIVE behaviour; it does something \
else. Answer "unchanged" for that as well, and say so in `reason`.

Be strict. Do not give the edit the benefit of the doubt. In `reason`, one or \
two sentences naming the lines that decided each answer."""


class _Verification(StrictResponseModel):
    before_does: Literal["expected", "defective", "cannot_tell"]
    after_does: Literal["expected", "defective", "unchanged", "cannot_tell"]
    reason: str


class EditVerdict(_Model):
    """What the verification call concluded about one edit."""

    verified: bool
    before_does: str
    after_does: str
    reason: str


def verify_edits(
    items: Sequence[tuple[Defect, MutationDescriptor, str]],
    client: ModelClient,
) -> list[EditVerdict]:
    """One verdict per `(defect, edit, source of the edited file)`, in input order.

    Calls are issued concurrently and returned in input order, so two runs over
    the same input record the same thing (`concurrency.py`, rule 2).
    """
    return map_calls(list(items), lambda item: _ask(item[0], item[1], item[2], client))


def verify_attempts(
    attempts: Sequence[MutationAttempt],
    defects: Sequence[Defect],
    sources: dict[str, str],
    client: ModelClient,
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
    )
    decided = {
        attempt.defect_id: verdict for attempt, verdict in zip(asking, verdicts, strict=True)
    }
    return [
        attempt.model_copy(
            update={
                "verified": decided[attempt.defect_id].verified,
                "verification_reason": _explain(decided[attempt.defect_id]),
            }
        )
        if attempt.defect_id in decided
        else attempt
        for attempt in attempts
    ]


def _ask(
    defect: Defect, descriptor: MutationDescriptor, source: str, client: ModelClient
) -> EditVerdict:
    messages = assemble(
        [
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            Block(BlockKind.SUBJECT, _subject(defect, descriptor, source)),
        ]
    )
    batch = partition([defect], 1, key=lambda d: d.id)[0]
    result = client.complete(
        messages,
        _Verification,
        batch.request_partition(),
        parse_as=_Verification,
        stage=_STAGE,
    )
    return EditVerdict(
        verified=result.before_does == "expected" and result.after_does == "defective",
        before_does=result.before_does,
        after_does=result.after_does,
        reason=result.reason.strip(),
    )


def _explain(verdict: EditVerdict) -> str:
    return (
        f"verification: before the edit the code does {verdict.before_does}, after it "
        f"{verdict.after_does}. {verdict.reason}"
    ).strip()


def _subject(defect: Defect, descriptor: MutationDescriptor, source: str) -> str:
    expected = defect.expected_behavior or "the opposite of the description below"
    defective = defect.defective_behavior or defect.description
    after = apply_span(source, descriptor)
    before_window = _window(source, descriptor.start_line, descriptor.end_line)
    new_end = descriptor.start_line + len(descriptor.replacement.splitlines()) - 1
    after_window = _window(after, descriptor.start_line, max(new_end, descriptor.start_line))
    return "\n".join(
        [
            "## The defect",
            f"description: {defect.description}",
            f"EXPECTED: {expected}",
            f"DEFECTIVE: {defective}",
            "",
            f"## BEFORE the edit — {descriptor.path}",
            before_window,
            "",
            f"## AFTER the edit — {descriptor.path}",
            after_window,
        ]
    )


def _window(text: str, start: int, end: int) -> str:
    lines = text.splitlines()
    first = max(1, start - CONTEXT_LINES)
    last = min(len(lines), end + CONTEXT_LINES)
    width = len(str(last))
    return "\n".join(
        f"{number:>{width}} | {lines[number - 1]}" for number in range(first, last + 1)
    )
