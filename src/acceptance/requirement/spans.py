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

__all__ = ["locate_in_text", "locate_within", "normalise", "offerable", "quotable_spans"]

# The double quote is refused inside a string literal by a strict response
# schema. Observed at #340's Gate 1, where a task file containing one aborted the
# whole review on an unhandled provider error:
#
#   Invalid schema for response_format '_Decomposition': In
#   context=(...,'source_quote'), " is not allowed in string literals for
#   structured outputs (strict=true)
#
# Substituting is the only repair that KEEPS the constraint. Dropping the enum
# for a requirement whose text happens to contain a quotation mark would let that
# call quote anything, which is exactly what `findings.md` §8 closed — and it
# would do it silently, on an input property nobody would think to look at.
#
# Only this character is known to be refused, because only this one has been
# observed. Another refused character would present the same way, and the repair
# is to extend these two constants together.
_REFUSED = '"'
_SUBSTITUTE = "”"  # RIGHT DOUBLE QUOTATION MARK

#: Characters `_SUBSTITUTE` may stand for when a quotation is matched back. The
#: substitution happens on the way out, so the source still holds the original
#: and the offered span holds the stand-in; matching has to accept either.
_INTERCHANGEABLE = frozenset({_REFUSED, _SUBSTITUTE, "“"})
_QUOTE_CLASS = "[" + "".join(sorted(re.escape(ch) for ch in _INTERCHANGEABLE)) + "]"

# A sentence ends at `.`, `?` or `!` followed by whitespace. Deliberately crude:
# this decides which quotations are OFFERED, and the whole block is always among
# them, so a split that misfires on an abbreviation costs a slightly odd extra
# choice rather than a quotation the requirement cannot express.
_SENTENCE_BREAK = re.compile(r"(?<=[.?!])\s+")


def normalise(text: str) -> str:
    """Runs of whitespace collapsed to one space, ends trimmed."""
    return " ".join(text.split())


def offerable(text: str) -> str:
    """One quotation as it may be OFFERED to the model.

    `normalise`, plus the substitution above. Kept separate from `normalise`
    rather than folded into it because the two have different jobs: `normalise`
    is used for comparisons that must see the text as written, and only a value
    on its way into a response schema needs to avoid a character the schema
    refuses.

    A span that contains no refused character comes back byte-identical, so the
    request a quotation-free mandate builds is unchanged and its recorded
    transcripts still replay.
    """
    return normalise(text).replace(_REFUSED, _SUBSTITUTE)


def quotable_spans(text: str) -> list[str]:
    """Every quotation a requirement of this text may offer, whole block first.

    The whole block leads because it is always a valid answer — a requirement
    that states one thing has nothing to narrow to — and because a model
    choosing from a list is offered the safe option first.

    Order is fixed and duplicates are dropped in first-seen order: the list
    becomes an enum inside the hashed request, so two runs over the same task
    file must build it identically.
    """
    whole = offerable(text)
    if not whole:
        return []
    offered = [whole]
    for sentence in _SENTENCE_BREAK.split(text):
        candidate = offerable(sentence)
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


def _word_pattern(word: str) -> str:
    """One word of a quotation, matching whichever quote character the text uses.

    The quotation was offered with `_SUBSTITUTE` where the source has `_REFUSED`,
    so a character-for-character match would reject the model's answer for a
    substitution we made ourselves — the same failure the whitespace handling
    above exists to prevent, on a different character.
    """
    return "".join(_QUOTE_CLASS if ch in _INTERCHANGEABLE else re.escape(ch) for ch in word)


def locate_in_text(haystack: str, offset: int, quote: str) -> TextSpan | None:
    """`quote` located in `haystack`, ignoring how either is wrapped.

    `offset` is where `haystack` begins in the file, so the returned span's
    `start`/`end` index the source rather than the fragment.
    """
    words = quote.split()
    if not words:
        return None
    pattern = re.compile(r"\s+".join(_word_pattern(word) for word in words))
    found = pattern.search(haystack)
    if found is None:
        return None
    start = offset + found.start()
    return TextSpan(
        text=haystack[found.start() : found.end()],
        start=start,
        end=start + (found.end() - found.start()),
    )
