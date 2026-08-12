"""Region-level total coverage of a task file (#216 deliverable 3).

The assertion this module exists to make: **every non-whitespace, non-heading
character of a task file lies inside a registry span or inside an `unclaimed`
span.** That is the direct form of DR-216 decision 1, and it is what makes the
`unread_source` guard's zero mean something.

It is deliberately stated over source *characters* rather than over a
requirement count. #216 shipped under a count that looked right: the registry
held three entries, `unclaimed` was empty, the CLI printed no unread-source
section, and three requirements were gone. A count cannot detect its own
missing entries, and neither can an assertion phrased in terms of one.

It is also deliberately independent of how `parse_task_file` walks the tree.
Enumerating "the blocks the parser descends into" and checking each has a span
would be circular — it would pass for any parser that is self-consistent,
including the one #216 reports. Characters are ground truth: they are in the
file whether or not the parser has a concept for them.

Two classes of character are excluded, because neither is content the
decomposer could read:

- **Headings.** Structure, not requirements; `parse_task_file` never spans them.
- **List markers and their indentation** — `- `, `* `, `1. `. These are syntax.
  The span for a bullet starts after its marker, so including them would fail
  every well-parsed file.

Excluding a character can only weaken the assertion, never produce a false
pass on dropped content: dropped content is the *text* of a block, and text is
neither a heading nor a marker.
"""

from __future__ import annotations

import re

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from acceptance.requirement.task_file import ParsedTaskFile, parse_task_file

__all__ = ["assert_total_region_coverage", "uncovered_regions"]

# A list marker at the head of a line, with its indentation and trailing space.
_MARKER = re.compile(r"^(\s*)([-*+]|\d+[.)])(\s+)")


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def _heading_positions(text: str) -> set[int]:
    """Every character position inside a heading node."""
    offsets = _line_offsets(text)
    positions: set[int] = set()
    for node in SyntaxTreeNode(MarkdownIt().parse(text)).walk():
        if node.type != "heading" or node.map is None:
            continue
        start_line, end_line = node.map
        start = offsets[start_line]
        end = offsets[end_line] if end_line < len(offsets) else len(text)
        positions.update(range(start, end))
    return positions


def _marker_positions(text: str) -> set[int]:
    positions: set[int] = set()
    for line_start, line in zip(_line_offsets(text), text.splitlines()):
        match = _MARKER.match(line)
        if match:
            positions.update(range(line_start, line_start + match.end()))
    return positions


def _accounted_positions(parsed: ParsedTaskFile) -> set[int]:
    """Every character position inside some span the parse produced.

    Registry spans and `unclaimed` spans together — the invariant is that a
    region is inside one or the other, and this assertion is not concerned with
    which. Whether a region reached the right *field* is a different question
    with its own tests; this one asks only whether it was accounted for at all.
    """
    positions: set[int] = set()
    for spans in (
        parsed.behavior,
        parsed.constraints,
        parsed.scope_exclusions,
        parsed.completion_expectations,
        parsed.unclaimed,
    ):
        for span in spans:
            positions.update(range(span.start, span.end))
    return positions


def uncovered_regions(text: str, parsed: ParsedTaskFile | None = None) -> list[tuple[int, str]]:
    """Contiguous runs of task-file content no span accounts for.

    Returns `(start_offset, text)` per run, so a failure names the dropped
    words rather than a character count.

    `parsed` defaults to this text's real parse. It is injectable so a test can
    supply a deliberately-damaged parse and prove this function detects a loss
    a requirement count cannot see — see
    `test_a_dropped_region_is_detected_when_the_requirement_count_is_unchanged`.
    """
    if parsed is None:
        parsed = parse_task_file(text)
    exempt = _heading_positions(text) | _marker_positions(text)
    accounted = _accounted_positions(parsed)

    # Maximal runs of missing characters. Whitespace breaks a run, so a dropped
    # sentence starts out as one run per word.
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for i, ch in enumerate(text):
        missing = not ch.isspace() and i not in exempt and i not in accounted
        if missing and start is None:
            start = i
        elif not missing and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(text)))

    # Rejoin runs separated only by whitespace, so a dropped paragraph is
    # reported as one region rather than as its individual words.
    merged: list[tuple[int, int]] = []
    for run_start, run_end in runs:
        if merged and text[merged[-1][1] : run_start].strip() == "":
            merged[-1] = (merged[-1][0], run_end)
        else:
            merged.append((run_start, run_end))

    return [(s, text[s:e]) for s, e in merged]


def assert_total_region_coverage(
    text: str, label: str, parsed: ParsedTaskFile | None = None
) -> None:
    """Fail with the dropped text itself, not a count of it."""
    uncovered = uncovered_regions(text, parsed)
    if not uncovered:
        return
    detail = "\n".join(f"  offset {start}: {run!r}" for start, run in uncovered)
    raise AssertionError(
        f"{label}: {len(uncovered)} region(s) of the task file are inside "
        f"neither a registry span nor an unclaimed span:\n{detail}"
    )
