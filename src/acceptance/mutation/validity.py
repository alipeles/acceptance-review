"""The five mechanical checks that decide whether a mutant may be injected.

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

For a file with no parser the other checks carry validity on their own, and the
containment check does the load-bearing work: the span must lie inside a region
the defect itself named, so a mutant cannot wander into an unrelated file.

The comments-and-whitespace check arrived later, and it is a *move* rather than
a new idea: `verification.py` already refused such an edit with no model call,
but only when `ExecutionSettings.verify_edits` was on, and that is off by
default. An edit that changes nothing is not a mutant whether or not anyone
asked to have edits verified, so the check belongs with the other mechanical
ones, which always run. `comparable` lives here and `verification.py` imports
it, so the two cannot answer the question differently.
"""

from __future__ import annotations

import ast
import io
import json
import tokenize
from collections.abc import Sequence

from acceptance.mutation.attempt import MutationDescriptor
from acceptance.mutation.region import Region

__all__ = [
    "DEFAULT_MAX_EDIT_LINES",
    "PYTHON_SUFFIXES",
    "apply_span",
    "changes_nothing",
    "comparable",
    "invalidity_reason",
]

#: How many lines one mutant may replace. Conservative by intent: the descriptor
#: is asked for the *smallest* edit that makes the named defect true, and a large
#: replacement is a sign the stage rewrote a function rather than broke it. Not a
#: measured value — this repository supplies counterexamples, never thresholds
#: (DR-170 Decision 6) — so it is configuration with a cautious default.
DEFAULT_MAX_EDIT_LINES = 12

#: Extensions whose files are parsed after the edit. A file whose extension is
#: not here is left to the other three checks, and that is the revision's point:
#: a missing parser is not a defect in the file.
#:
#: **It is a list of parsers we have, not a claim about which files are
#: parseable.** Gate 2 of #45 found the gap that distinction hides — with only
#: Python here, a mutated `.json` passed validity however malformed it was,
#: while the requirement is that a file *that has a parser* still parses. Any
#: format the checker can parse without a new dependency belongs here.
#:
#: `tomllib` is deliberately absent: it arrives in Python 3.11 and this project
#: runs 3.10, so adding it would be a parse check that silently does nothing.
_PARSERS = {
    ".py": ast.parse,
    ".pyi": ast.parse,
    ".json": json.loads,
}

#: What each parser raises on malformed input. Caught by type rather than by a
#: bare `except Exception`, so a bug *in* a parser surfaces as a crash instead of
#: being reported as an invalid mutant — which would silently refuse every edit
#: to that file type and look like the mutation stage working.
_PARSE_ERRORS = (SyntaxError, ValueError)

#: Files whose comments are known and can be removed before comparing.
PYTHON_SUFFIXES = (".py", ".pyi")

#: Token types that carry a statement's place in the block structure rather than
#: its text. Kept in the comparison as their names, so re-indenting a whole block
#: by the same amount compares equal while moving a statement out of a block does
#: not — the second changes behaviour and the first does not.
_LAYOUT = {tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}


def comparable(path: str, text: str) -> list[str]:
    """`text` with comments and whitespace removed, for deciding whether an edit
    changed anything but those.

    For Python the token stream, minus comments and blank lines, with indentation
    kept as structure rather than width. Anything else, or Python that does not
    tokenize, compares as its words.

    Moved here from `verification.py` so the always-on gate and the verifier
    cannot disagree about what "changes nothing" means.
    """
    if path.endswith(PYTHON_SUFFIXES):
        try:
            return [
                tokenize.tok_name[token.type] if token.type in _LAYOUT else token.string
                for token in tokenize.generate_tokens(io.StringIO(text).readline)
                if token.type not in (tokenize.COMMENT, tokenize.NL)
            ]
        except (tokenize.TokenError, SyntaxError):
            pass
    return text.split()


def changes_nothing(descriptor: MutationDescriptor, source: str) -> bool:
    """Whether the edit is identical to what it replaces, or differs only in
    comments or whitespace — checks 5 and 6 of `invalidity_reason` together.

    Separate so a caller can tell *which kind* of refusal it got without
    parsing the reason text: #334 records an edit that changed nothing apart
    from one that failed any other check.

    A span running past the end of the file is not "nothing changed" — it fails
    check 1 — and is answered `False` so it is never counted as both.
    """
    if descriptor.end_line > len(source.splitlines()):
        return False
    replaced = "".join(
        source.splitlines(keepends=True)[descriptor.start_line - 1 : descriptor.end_line]
    )
    if replaced == descriptor.replacement:
        return True
    return comparable(descriptor.path, source) == comparable(
        descriptor.path, apply_span(source, descriptor)
    )


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

    # Check 5 — it changes something. A replacement identical to the lines it
    # replaces is not a mutant: nothing can fail on it, so every candidate test
    # "survives" and the criterion is recorded as having tests that do not
    # discriminate. **That is a false finding against the builder**, and the
    # silent kind — a survival reads exactly like a real one.
    #
    # Measured, not anticipated: four of twelve descriptors sampled at #45's
    # Gate 2 returned text byte-identical to the original, one of them merely
    # deleting a blank line. Reported as `not_mutable`, which is the honest
    # answer — the stage was asked for an edit and did not produce one.
    replaced = "".join(
        source.splitlines(keepends=True)[descriptor.start_line - 1 : descriptor.end_line]
    )
    if replaced == descriptor.replacement:
        return (
            f"the replacement for {descriptor.path} lines {descriptor.start_line}.."
            f"{descriptor.end_line} is identical to what it replaces, so nothing would be "
            "injected and every test would 'survive' a defect that was never introduced"
        )

    # Check 6 — it changes something a reader would call a change. Check 5
    # catches only byte equality, so an edit that adds a comment, reflows a
    # line or re-indents a whole block passes it and injects nothing. The
    # consequence is check 5's, exactly: every candidate test "survives" a
    # defect that was never introduced, and the criterion is recorded as having
    # tests that do not discriminate — a false finding against the builder, and
    # a silent one.
    #
    # Ordered after check 5 so a byte-identical edit keeps its own, more
    # specific reason.
    if comparable(descriptor.path, source) == comparable(
        descriptor.path, apply_span(source, descriptor)
    ):
        return (
            f"the replacement for {descriptor.path} lines {descriptor.start_line}.."
            f"{descriptor.end_line} differs from what it replaces only in comments or "
            "whitespace, so nothing would be injected and every test would 'survive' a "
            "defect that was never introduced"
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
        except _PARSE_ERRORS as error:
            return f"the mutated {descriptor.path} does not parse: {error}"

    return None


def _parser_for(path: str):
    for suffix, parse in _PARSERS.items():
        if path.endswith(suffix):
            return parse
    return None
