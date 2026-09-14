"""The four mechanical checks that decide whether a mutant may be injected.

DR-171 Decision 3, as revised 2026-09-14. Deliberately *mechanical*: no second
model call confirms that the edit really violates the obligation. Such a call
would be judging its own output, would cost a call per defect, and would produce
a claim at the same tier as the thing it is checking. What replaces it is
recording the mutant text so a reader can disagree with it.

The revision is the parse check. It used to run `ast.parse` on every mutated
file, which failed closed on anything Python cannot read and so silently made
every documentation defect unmutable. That was never argued for; it fell out of
writing the check in terms of Python. A span replacement is text, and a
requirement stated in prose can be broken in prose — the tests that read that
prose are exactly the ones that catch it.

For a file with no parser the other three checks carry validity on their own,
and the containment check does the load-bearing work: the span must lie inside a
region the defect itself named, so a mutant cannot wander into an unrelated
file.
"""

from __future__ import annotations

import ast
from collections.abc import Sequence

from acceptance.mutation.attempt import MutationDescriptor
from acceptance.mutation.region import Region

__all__ = ["DEFAULT_MAX_EDIT_LINES", "apply_span", "invalidity_reason"]

#: How many lines one mutant may replace. Conservative by intent: the descriptor
#: is asked for the *smallest* edit that makes the named defect true, and a large
#: replacement is a sign the stage rewrote a function rather than broke it. Not a
#: measured value — this repository supplies counterexamples, never thresholds
#: (DR-170 Decision 6) — so it is configuration with a cautious default.
DEFAULT_MAX_EDIT_LINES = 12

#: Extensions whose files are parsed after the edit. Everything else is left to
#: the other three checks. A missing parser is not a defect in the file.
_PARSERS = {".py": ast.parse}


def apply_span(source: str, descriptor: MutationDescriptor) -> str:
    """`source` with the descriptor's line span replaced.

    Line endings are preserved by splitting on them rather than normalising: a
    mutant that silently rewrote every line ending would change the file far
    beyond its named region, and the diff a reader inspects afterwards would be
    unreadable.
    """
    lines = source.splitlines(keepends=True)
    head = lines[: descriptor.start_line - 1]
    tail = lines[descriptor.end_line :]
    replacement = [descriptor.replacement] if descriptor.replacement else []
    return "".join([*head, *replacement, *tail])


def invalidity_reason(
    descriptor: MutationDescriptor,
    regions: Sequence[Region],
    source: str,
    max_edit_lines: int = DEFAULT_MAX_EDIT_LINES,
) -> str | None:
    """Why this mutant may not be injected, or `None` if it may.

    A reason rather than a boolean, because the caller records it: a defect that
    could not be mutated is `not_mutable` *with the reason it was not*, and an
    outcome saying only "no" is indistinguishable from one nobody looked at.
    """
    # Check 1 — it applies. A span replacement applies by construction only if
    # the lines it names exist; a descriptor pointing past the end of the file
    # would otherwise silently append.
    line_count = len(source.splitlines())
    if descriptor.end_line > line_count:
        return (
            f"the span {descriptor.start_line}..{descriptor.end_line} runs past the end of "
            f"{descriptor.path}, which has {line_count} line(s)"
        )

    # Check 4 — the edit is bounded. Checked before the parse so an enormous
    # replacement is reported as oversized rather than as a syntax error.
    if descriptor.line_count > max_edit_lines:
        return (
            f"the edit replaces {descriptor.line_count} lines, over the {max_edit_lines}-line "
            "bound; the smallest edit that makes the defect true is what was asked for"
        )

    # Check 3 — containment. The load-bearing one, and the only thing standing
    # between a mutant and unrelated code once the parse check stops being
    # universal.
    named = [region for region in regions if region.path == descriptor.path]
    if not named:
        return (
            f"the defect names no region in {descriptor.path}, so an edit there could not be "
            "credited to it"
        )
    if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
        spans = ", ".join(f"{region.start_line}..{region.end_line}" for region in named)
        return (
            f"the span {descriptor.start_line}..{descriptor.end_line} falls outside the "
            f"region(s) the defect named in {descriptor.path} ({spans})"
        )

    # Check 2 — the mutated file parses, when the file has a parser.
    parse = _parser_for(descriptor.path)
    if parse is not None:
        mutated = apply_span(source, descriptor)
        try:
            parse(mutated)
        except SyntaxError as error:
            return f"the mutated {descriptor.path} does not parse: {error}"

    return None


def _parser_for(path: str):
    for suffix, parse in _PARSERS.items():
        if path.endswith(suffix):
            return parse
    return None
