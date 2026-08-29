"""The quotations one requirement may offer, and how to find one again (#317).

A decompose call is asked about one requirement and is offered that
requirement's own spans as the values `source_quote` may take. An obligation
about some other requirement then has no quotation available to it, so it is
unsayable rather than detected afterwards — the standard `DR-163` set, applied
to the field that actually carries the violation.

`docs/experiments/317-over-answering/findings.md` §8 is why it is this field and
not `requirement_id`. The id was already an enum, and the model wrote eleven
entries about the constraints while labelling every one of them `task-01`: an
enum restricts the label, not what the entry is about. `source_quote` was the
only unconstrained field, and it is the one that says which text an obligation
came from.

**Spans are offered whitespace-normalised and matched back the same way.** Task
prose is hard-wrapped, so the same sentence appears with a newline in one place
and a space in another; a character-for-character test would then reject a
quotation for a property of the file's line width. `locate_within` returns the
real offsets into the source, so the obligation still carries an honest
`TextSpan` (CLAUDE.md's typed-and-linked invariant).
"""

from __future__ import annotations

import re

from acceptance.review_state import RequirementRef
from acceptance.source_ref import TextSpan

__all__ = ["locate_in_text", "locate_within", "normalise", "quotable_spans"]

# A sentence ends at `.`, `?` or `!` followed by whitespace. Deliberately crude:
# this decides which quotations are OFFERED, and the whole block is always among
# them, so a split that misfires on an abbreviation costs a slightly odd extra
# choice rather than a quotation the requirement cannot express.
_SENTENCE_BREAK = re.compile(r"(?<=[.?!])\s+")


def normalise(text: str) -> str:
    """Runs of whitespace collapsed to one space, ends trimmed."""
    return " ".join(text.split())


def quotable_spans(text: str) -> list[str]:
    """Every quotation a requirement of this text may offer, whole block first.

    The whole block leads because it is always a valid answer — a requirement
    that states one thing has nothing to narrow to — and because a model
    choosing from a list is offered the safe option first.

    Order is fixed and duplicates are dropped in first-seen order: the list
    becomes an enum inside the hashed request, so two runs over the same task
    file must build it identically.
    """
    whole = normalise(text)
    if not whole:
        return []
    offered = [whole]
    for sentence in _SENTENCE_BREAK.split(text):
        candidate = normalise(sentence)
        if candidate and candidate not in offered:
            offered.append(candidate)
    return offered


def locate_within(requirement: RequirementRef, quote: str) -> TextSpan | None:
    """Where `quote` sits inside `requirement`'s own text, or None if it does not.

    **Only inside that requirement.** The retired `_locate_quotation` searched
    the whole file and re-filed an obligation onto whichever requirement its
    quotation landed in, which is how a call answering for the Constraints
    section had its work scattered across eleven requirements another call had
    already derived properly (`findings.md` §4). A call now answers for one
    requirement, so a quotation that is not inside it is an unusable answer, not
    a routing instruction.
    """
    return locate_in_text(requirement.span.text, requirement.span.start, quote)


def locate_in_text(haystack: str, offset: int, quote: str) -> TextSpan | None:
    """`quote` located in `haystack`, ignoring how either is wrapped.

    `offset` is where `haystack` begins in the file, so the returned span's
    `start`/`end` index the source rather than the fragment.
    """
    words = quote.split()
    if not words:
        return None
    pattern = re.compile(r"\s+".join(re.escape(word) for word in words))
    found = pattern.search(haystack)
    if found is None:
        return None
    start = offset + found.start()
    return TextSpan(
        text=haystack[found.start() : found.end()],
        start=start,
        end=start + (found.end() - found.start()),
    )
