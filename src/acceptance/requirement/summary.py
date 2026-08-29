"""Accounting for the mandate's opening summary, last and on its own (#317).

A task file states a change as an opening summary and then elaborates it as
bullets. The registry treats the summary as a peer of the bullets (`DR-216`),
and for bullets that is right — over the recorded corpus, 0 of 68 decompose
calls with no `task-*` requirement in their answering set derived an obligation
for a requirement they were not asked about. With the summary in the answering
set the rate is 8 of 35 (`docs/experiments/317-over-answering/findings.md` §2).
The summary is the parent of every other requirement, so "what obligations does
this paragraph impose" has no bounded answer, and the model gives the unbounded
one.

So the summary is accounted for **last**, against the obligations the rest of
the mandate has already produced, by a step that divides it into spans of its
own words and decides each span separately. Two properties make that step safe:

- **It yields no obligations at all.** It returns a partition and a verdict per
  span; obligations for the spans it leaves uncovered are authored afterwards by
  the ordinary per-requirement decomposer, which is the shape that over-answers
  0 times in 68.
- **The verdict follows the argument rather than justifying it.** `nearest` and
  `counterexample` are written before `disposition`, and a verdict disagreeing
  with what was written is rejected. The `covered`/`uncovered` union shape put
  the verdict in the shape selector — the opposite ordering — and marked every
  span covered in 5 of 5 draws while its own prose named the gap.

**Do not solve this by making the summary context-only.** Across the 30 recorded
reviews carrying a requirement map, 173 of 738 obligations (23%) come from
`task-*` requirements, and on a lexical proxy only 40 of those reach 0.35
overlap with the closest bullet-derived obligation. Silencing the paragraph
risks losing requirements, which is the one failure this project treats as
worst.

Measured over 20 draws on two mandates, this shape never once marked a genuinely
uncovered property as covered. It marked a covered property as uncovered in 4 of
20, which yields a duplicate obligation rather than a lost requirement — the
milder failure, and the one the linking stage already exists to handle.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from acceptance.llm import ModelClient, SchemaValidationError, StrictResponseModel
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.requirement.spans import normalise
from acceptance.review_state import Obligation, RequirementRef
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

# Its own stage name, so its spend, its partitioning and — the point of the
# separation — its model are attributed to it rather than to `decompose`.
SUMMARY_STAGE = "decompose-summary"

# `docs/experiments/317-over-answering/prompts-v2-baseline/phase2-system-v7-neutral-frame.txt`,
# verbatim. It is the arm the experiment settled on and the draws that scored it
# were taken against exactly this text; re-wording it would discard the
# measurement along with the transcripts.
_SYSTEM_PROMPT = """\
You decide, for each property a summary paragraph states, whether a list of
obligations already requires it.

A task file states a change as an opening summary and then elaborates it as
bullets. Every bullet has already been decomposed into obligations, and you are
given all of them by id, description and type. You are given the summary. The
summary is the only text you may quote.

Work in two steps, and return both.

First, divide the summary into spans. A span is a stretch of the summary's own
words that states one property the delivered code must have. Split where two
properties are joined: "and", "and that", or a comma between two predicates.
Do not split a qualifier from the predicate it qualifies: "Before X, the
system does Y" states one property, that Y happens before X, and is one span.
Every property the summary states belongs to exactly one span; spans do not
overlap; words that state no property belong to no span. Copy each span
character for character.

Then, for each span in order, try to build a counterexample: a change that
satisfies every listed obligation close to the span and still lacks the
property the span states. Put those obligations' ids in `nearest`; if nothing
on the list is close, leave it empty. In `counterexample`, describe the change
concretely: what it does that satisfies each obligation in `nearest`, and what
it does or omits so that the span's property does not hold. A counterexample
is a change that could actually be built; if the change you describe both has
the property and lacks it, it is not one. If you wrote a counterexample, the
span is `uncovered`. If no such change can exist, because satisfying the
obligations in `nearest` forces the property, write the single word `none` and
mark the span `covered`.

An obligation that makes a property possible does not force it. If an
obligation says every order carries a timestamp, a change can still sort
orders by id; the timestamp does not force sorting by it. If an obligation says
what inputs a step receives, a change can still run that step at any point in
the run; the inputs do not force an order.

You return no obligations. Uncovered spans become obligations afterwards; your
job ends at the verdict.
"""


class _SpanVerdict(StrictResponseModel):
    """One span's argument, and only then its verdict.

    **Field order is the mechanism, not presentation.** The model writes which
    obligations are nearest, then the counterexample, and only then the
    disposition, so the verdict is produced after the argument rather than
    justified backwards from it. A tagged union of a covered shape and an
    uncovered shape puts the verdict in the shape selector, which is the
    opposite ordering; that arm answered `covered` on every span of every draw
    while its own `covered_because` prose named the gap.
    """

    span_index: int
    nearest: list[str]
    counterexample: str
    disposition: Literal["uncovered", "covered"]


class _SummarySpans(StrictResponseModel):
    """The partition, then the verdicts over it.

    `spans` comes first so the model commits to a division of the summary before
    it says anything about coverage. In the shape this replaces the partition
    happened in the model's head and only its conclusions were visible, so
    nothing could check that every property had been considered exactly once.
    """

    spans: list[str]
    span_dispositions: list[_SpanVerdict]


@dataclass(frozen=True)
class SpanDecision:
    """One span of the summary, and whether the derived obligations require it."""

    index: int
    text: str
    covered: bool
    nearest: tuple[str, ...]
    counterexample: str


def listed_obligations(obligations: Sequence[Obligation]) -> str:
    """The derived obligations as id, description and type, and nothing else.

    No bullet text and no quotations, deliberately. The bullets are what the
    summary elaborates, and showing them is what invites an answer about them —
    which is the defect this whole step exists to remove.
    """
    return "\n".join(
        f"[{obligation.id}] ({obligation.type.value}) {obligation.description}"
        for obligation in obligations
    )


def _user_prompt(obligations: Sequence[Obligation], summary_text: str) -> str:
    return "\n".join(
        [
            "Obligations already derived from the bullets:",
            "",
            listed_obligations(obligations),
            "",
            "The summary:",
            "",
            summary_text,
        ]
    )


def _is_none(counterexample: str) -> bool:
    """The single word `none`, allowing surrounding space and a full stop."""
    return normalise(counterexample).lower().rstrip(".") == "none"


def _rejection(parsed: _SummarySpans, summary_text: str, listed_ids: set[str]) -> str | None:
    """Why this answer cannot be used, or None if it can.

    Four checks, and each is a completion expectation of #317 rather than a
    defensive extra: every span is a substring of the summary; every span is
    decided exactly once; `nearest` names only obligations that were shown; and
    the verdict agrees with whether a counterexample was written.

    The substring test collapses runs of whitespace on both sides. The summary is
    hard-wrapped in the task file, so a character-for-character test would reject
    a span for containing a space where the source has a newline — a property of
    the file's line width, not of the answer.
    """
    haystack = normalise(summary_text)
    for index, span in enumerate(parsed.spans):
        if normalise(span) not in haystack:
            return f"span {index} is not a substring of the summary: {span!r}"

    seen: dict[int, int] = {}
    for entry in parsed.span_dispositions:
        if not 0 <= entry.span_index < len(parsed.spans):
            return f"span_index {entry.span_index} is out of range ({len(parsed.spans)} span(s))"
        seen[entry.span_index] = seen.get(entry.span_index, 0) + 1
    for index in range(len(parsed.spans)):
        count = seen.get(index, 0)
        if count != 1:
            return f"span {index} was decided {count} times, not once"

    for entry in parsed.span_dispositions:
        for obligation_id in entry.nearest:
            if obligation_id not in listed_ids:
                return f"nearest names {obligation_id!r}, which was not on the list shown"
        wrote_counterexample = not _is_none(entry.counterexample)
        if entry.disposition == "covered" and wrote_counterexample:
            return (
                f"span {entry.span_index} is covered but its counterexample is not the "
                f"single word 'none': {entry.counterexample!r}"
            )
        if entry.disposition == "uncovered" and not wrote_counterexample:
            return f"span {entry.span_index} is uncovered but wrote no counterexample"
    return None


def decide_spans(
    summary: RequirementRef,
    obligations: Sequence[Obligation],
    client: ModelClient,
    unusable_answers: UnusableAnswerLog | None = None,
) -> list[SpanDecision]:
    """Divide the summary into spans and decide each one against `obligations`.

    Returns no obligations, by construction: this step's whole output is a
    partition and a verdict per span.

    **A rejected answer is not retried.** The request is content-addressed, so a
    second identical call would be served the identical recorded response for
    ever; and with temperature and seed pinned, a request that differed only by
    an attempt counter would draw the same answer anyway. A malformed partition
    is therefore an unusable answer that stops the run, which is the same stance
    `_requirement_map` takes on a response that does not account for the mandate:
    a review whose summary was never divided is not a review with a gap in it.
    """
    listed_ids = {obligation.id for obligation in obligations}
    messages = assemble(
        [
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            Block(BlockKind.SUBJECT, _user_prompt(obligations, summary.span.text)),
        ]
    )
    allowed = {"nearest": sorted(listed_ids)}
    parsed = client.complete(
        messages,
        constrain(_SummarySpans, allowed),
        parse_as=_SummarySpans,
        stage=SUMMARY_STAGE,
    )
    if unusable_answers is not None:
        unusable_answers.record(scan(parsed, allowed, SUMMARY_STAGE))

    reason = _rejection(parsed, summary.span.text, listed_ids)
    if reason is not None:
        if unusable_answers is not None:
            unusable_answers.record(
                [
                    UnusableAnswer(
                        stage=SUMMARY_STAGE,
                        field="span_dispositions",
                        returned_id=summary.id,
                        reason=reason,
                    )
                ]
            )
        raise SchemaValidationError(
            f"the summary pass over requirement '{summary.id}' returned a partition "
            f"that cannot be used: {reason}"
        )

    if not parsed.spans and unusable_answers is not None:
        # Not an error — a summary really can state nothing the bullets do not —
        # but it is also how "mark everything covered" would look, and that
        # failure was observed on the smaller model. Recorded so it is visible
        # rather than inferred from an empty obligation list.
        unusable_answers.record(
            [
                UnusableAnswer(
                    stage=SUMMARY_STAGE,
                    field="spans",
                    returned_id=summary.id,
                    reason="the summary was divided into no spans, so it states no property",
                )
            ]
        )

    return [
        SpanDecision(
            index=entry.span_index,
            text=parsed.spans[entry.span_index],
            covered=entry.disposition == "covered",
            nearest=tuple(entry.nearest),
            counterexample=entry.counterexample,
        )
        # Span order, not response order, so two runs over the same input build
        # the obligation list identically (M0.5).
        for entry in sorted(parsed.span_dispositions, key=lambda entry: entry.span_index)
    ]


def coverage_reason(decisions: Sequence[SpanDecision]) -> str:
    """Why a summary that yielded nothing yielded nothing.

    Every span, with the obligations that were held to force it. A
    `no_obligation` disposition must carry a reason, and the reason a reader
    needs here is which already-derived obligations the summary was measured
    against — not the bare fact that it produced nothing.
    """
    if not decisions:
        return (
            "the summary was divided into no spans, so it states no property of its own "
            "for the delivered change to have"
        )
    parts = [
        f"{normalise(decision.text)!r} -> "
        + (", ".join(decision.nearest) if decision.nearest else "no obligation named")
        for decision in decisions
    ]
    return (
        "every property this summary states is already required by obligations derived "
        "from the rest of the mandate: " + "; ".join(parts)
    )
