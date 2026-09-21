"""Checks that an edit really makes its named defect true, before its result counts.

The tier gate in `attempt.py` lets an observed kill or survival reach
`DEFECT_KILLED` only once its edit is verified. This is the verification: two
questions per observed edit, asked in sequence (#335).

1. **Behaviour change.** Does the edit change what the code does at all? Both
   versions are first compared with comments and whitespace removed; an edit
   that differs in nothing else is refused with no model call, since no answer
   could be in doubt. Otherwise a model is asked, shown the code without its
   comments and NOT shown the defect. An edit it says changes nothing is refused
   here; one it cannot decide about goes on to the second question rather than
   being refused for want of an answer.
2. **Defect match.** Only for an edit that changes behaviour: did the code have
   the defect's expected behaviour before the edit, and its defective behaviour
   after it? Anything else is refused, including an edit to code that already
   had the defective behaviour.

The single question this replaced asked for both at once, and conflated an edit
that changes nothing with one that changes the wrong thing. The refusing
question is recorded on the attempt (`VerificationStep`) so the two can be
counted apart.

**It reverses DR-171 Decision 3**, which ruled out a confirming model call. The
measurement that reversal rests on — what share of known-bad edits this catches,
and what share of known-good ones it wrongly rejects — is recorded in DR-171, and
the stage is off by default (`ExecutionSettings.verify_edits`) until it is
adopted on those numbers.

Neither question is shown the tests or what they did: the question is whether
the edit makes the defect true, and knowing which tests failed would invite
judging the edit by its outcome.
"""

from __future__ import annotations

import io
import tokenize
from collections.abc import Sequence
from typing import Literal

from acceptance.change.context import RetrievalResult
from acceptance.concurrency import map_calls
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel as _Model
from acceptance.mutation.attempt import MutationAttempt, MutationDescriptor, VerificationStep
from acceptance.mutation.surrounding import contexts_for, render_contexts
from acceptance.mutation.validity import apply_span
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import Defect

__all__ = ["CONTEXT_LINES", "EditVerdict", "verify_attempts", "verify_edits"]

_CHANGE_STAGE = "mutation verification: behaviour change"
_MATCH_STAGE = "mutation verification: defect match"

#: Lines of unchanged code shown on each side of the edit. Enough to see the
#: enclosing function in most code, without shipping whole files per call.
CONTEXT_LINES = 30

#: Files whose comments are known and can be removed before comparing.
_PYTHON = (".py", ".pyi")

_CHANGE_PROMPT = """You check whether ONE edit to a codebase changes what the \
code does.

You are given the code around one edit, BEFORE the edit and AFTER it, with \
comments removed. Lines that held only a comment or nothing are left out; the \
line numbers are the file's own.

Answer `changes_behaviour`:
- "changes" when some input or state makes the AFTER code do something the \
BEFORE code did not: a different return value, side effect, exception, or output.
- "no_change" when the two do the same thing for every input — for example the \
edit renames a local name consistently, reorders independent statements, adds a \
condition that is always true, or rewrites an expression into an equivalent one.
- "cannot_tell" when the code shown is not enough to decide.

You are not told what the edit was for. Judge only whether the behaviour \
differs, not whether the difference is a good one. In `reason`, one or two \
sentences naming the lines that decided it."""

_MATCH_PROMPT = """You check whether ONE edit to a codebase does what it was \
meant to do.

You are given a named defect, stated as two behaviours:
- EXPECTED: what the code must do.
- DEFECTIVE: what the code would do if the defect were present.

You are also given the code around one edit, BEFORE the edit and AFTER it. The \
edit is already known to change the code's behaviour.

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


class _BehaviourChange(StrictResponseModel):
    changes_behaviour: Literal["changes", "no_change", "cannot_tell"]
    reason: str


class _Verification(StrictResponseModel):
    before_does: Literal["expected", "defective", "cannot_tell"]
    after_does: Literal["expected", "defective", "other", "cannot_tell"]
    reason: str


class EditVerdict(_Model):
    """What verification concluded about one edit.

    `refused_by` names the question that refused it, and is empty for a verified
    edit. `before_does` and `after_does` are empty when the second question was
    never asked.
    """

    verified: bool
    refused_by: VerificationStep | None = None
    changes_behaviour: str
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
    the same input record the same thing (`concurrency.py`, rule 2). Each edit's
    two questions are asked in sequence, since the second depends on the first.
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
    if _comparable(descriptor.path, source) == _comparable(descriptor.path, after):
        return EditVerdict(
            verified=False,
            refused_by=VerificationStep.BEHAVIOUR_CHANGE,
            changes_behaviour="no_change",
            reason="the edit changes only comments or whitespace",
        )
    spans = [(descriptor.path, descriptor.start_line, descriptor.end_line)]
    # Shows the code BEFORE the edit, like the edit-building call saw it.
    context = render_contexts(contexts_for(spans, surrounding))
    partition_key = partition([defect], 1, key=lambda d: d.id)[0].request_partition()

    change = client.complete(
        _messages(_CHANGE_PROMPT, _code(descriptor, source, after, stripped=True), context),
        _BehaviourChange,
        partition_key,
        parse_as=_BehaviourChange,
        stage=_CHANGE_STAGE,
    )
    if change.changes_behaviour == "no_change":
        return EditVerdict(
            verified=False,
            refused_by=VerificationStep.BEHAVIOUR_CHANGE,
            changes_behaviour=change.changes_behaviour,
            reason=change.reason.strip(),
        )

    match = client.complete(
        _messages(
            _MATCH_PROMPT,
            f"{_defect_block(defect)}\n\n{_code(descriptor, source, after, stripped=False)}",
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
        changes_behaviour=change.changes_behaviour,
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
            f"verification refused the edit at its first question: the edit does not "
            f"change the code's behaviour. {verdict.reason}"
        ).strip()
    outcome = "verified" if verdict.verified else "refused at its second question"
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


def _code(descriptor: MutationDescriptor, before: str, after: str, *, stripped: bool) -> str:
    """The code around the edit, before and after it, optionally without comments."""
    new_end = descriptor.start_line + len(descriptor.replacement.splitlines()) - 1
    before_lines = _lines(descriptor.path, before, stripped=stripped)
    after_lines = _lines(descriptor.path, after, stripped=stripped)
    return "\n".join(
        [
            f"## BEFORE the edit — {descriptor.path}",
            _window(before_lines, descriptor.start_line, descriptor.end_line, stripped),
            "",
            f"## AFTER the edit — {descriptor.path}",
            _window(
                after_lines, descriptor.start_line, max(new_end, descriptor.start_line), stripped
            ),
        ]
    )


def _lines(path: str, text: str, *, stripped: bool) -> list[str]:
    """`text`'s lines, one per file line, with comments removed when `stripped`.

    Only Python comments are known; any other file keeps its text, and a Python
    file that does not tokenize keeps its comments rather than losing lines.
    """
    lines = text.splitlines()
    if not stripped:
        return lines
    if path.endswith(_PYTHON):
        try:
            cut = list(lines)
            for token in tokenize.generate_tokens(io.StringIO(text).readline):
                row, column = token.start
                if token.type == tokenize.COMMENT and row <= len(cut):
                    cut[row - 1] = cut[row - 1][:column]
            lines = cut
        except (tokenize.TokenError, SyntaxError):
            pass
    return [line.rstrip() for line in lines]


def _comparable(path: str, text: str) -> list[str]:
    """`text` with comments and whitespace removed, for deciding whether an edit
    changed anything but those.

    For Python the token stream, minus comments and blank lines, with indentation
    kept as structure rather than width: moving a statement out of a block
    changes behaviour, re-indenting a whole block by the same amount does not.
    Anything else, or Python that does not tokenize, compares as its words.
    """
    if path.endswith(_PYTHON):
        try:
            return [
                tokenize.tok_name[token.type] if token.type in _LAYOUT else token.string
                for token in tokenize.generate_tokens(io.StringIO(text).readline)
                if token.type not in (tokenize.COMMENT, tokenize.NL)
            ]
        except (tokenize.TokenError, SyntaxError):
            pass
    return text.split()


_LAYOUT = {tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}


def _window(lines: list[str], start: int, end: int, skip_blank: bool = False) -> str:
    first = max(1, start - CONTEXT_LINES)
    last = min(len(lines), end + CONTEXT_LINES)
    width = len(str(last))
    return "\n".join(
        f"{number:>{width}} | {lines[number - 1]}"
        for number in range(first, last + 1)
        if not (skip_blank and not lines[number - 1].strip())
    )
