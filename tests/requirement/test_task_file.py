from pathlib import Path

import pytest

from acceptance.requirement.task_file import ParsedTaskFile, parse_task_file
from tests.requirement.corpus import committed_task_files

# The exact §7.1 example from the spec.
SPEC_EXAMPLE = """# Task
Add support for indirect circular references.

## Constraints
- Do not evaluate formulas involved in a cycle.
- Return the complete cycle path.
- Preserve current direct-cycle behavior.

## Completion expectations
- Implementation
- Unit tests
- Documentation update
"""


def _texts(spans):
    return [s.text for s in spans]


def test_spec_example_fields_match_expected():
    parsed = parse_task_file(SPEC_EXAMPLE)

    assert [b.text for b in parsed.behavior] == ["Add support for indirect circular references."]
    assert _texts(parsed.constraints) == [
        "Do not evaluate formulas involved in a cycle.",
        "Return the complete cycle path.",
        "Preserve current direct-cycle behavior.",
    ]
    assert _texts(parsed.completion_expectations) == [
        "Implementation",
        "Unit tests",
        "Documentation update",
    ]
    assert parsed.scope_exclusions == []


def test_every_extracted_item_retains_a_source_reference():
    parsed = parse_task_file(SPEC_EXAMPLE)

    spans = [*parsed.behavior, *parsed.constraints, *parsed.completion_expectations]
    for span in spans:
        # The source reference is real: the span points at exactly its text.
        assert SPEC_EXAMPLE[span.start : span.end] == span.text


def test_scope_exclusions_are_parsed_when_present():
    text = """# Task
Do the thing.

## Scope exclusions
- Not the legacy path.
- Not the CLI.
"""
    parsed = parse_task_file(text)
    assert _texts(parsed.scope_exclusions) == ["Not the legacy path.", "Not the CLI."]
    for span in parsed.scope_exclusions:
        assert text[span.start : span.end] == span.text


def test_unknown_sections_are_ignored():
    text = """# Task
Do the thing.

## Notes
- ignore me

## Constraints
- keep this
"""
    parsed = parse_task_file(text)
    assert _texts(parsed.constraints) == ["keep this"]
    assert parsed.scope_exclusions == []
    assert parsed.completion_expectations == []


def test_missing_sections_yield_empty_fields():
    parsed = parse_task_file("# Task\nJust a behavior, nothing else.\n")
    assert [b.text for b in parsed.behavior] == ["Just a behavior, nothing else."]
    assert parsed.constraints == []
    assert parsed.completion_expectations == []
    assert parsed.scope_exclusions == []


def test_roundtrips_through_persistence():
    parsed = parse_task_file(SPEC_EXAMPLE)
    assert ParsedTaskFile.from_dict(parsed.to_dict()) == parsed


@pytest.mark.parametrize("path", committed_task_files(), ids=lambda p: p.parent.name)
def test_parses_every_committed_task_file(path: Path):
    """Covers the committed corpus — every `dogfood-logs/*/current-task.md` —
    and deliberately not the repository-root `current-task.md` (#258).

    This asserted a property of *the task in flight* before, which is not a
    property of the software at all: it passed or failed on whatever had been
    written for the current piece of work. The corpus is a strictly better
    regression guard — larger, stable, growing with each dogfood run, and every
    entry governed by a commit.
    """
    parsed = parse_task_file(path.read_text())

    assert parsed.behavior
    assert parsed.constraints  # every committed task file lists constraints

    # Completion expectations are deliberately NOT asserted to be present.
    # CLAUDE.md's task-file style makes the section optional — "if the section
    # appears, keep it at the spec §7.1 example's grain" — because re-listing
    # every behavior there does Gate 1's decomposition at authoring time. The
    # section happened to appear in every earlier file, so asserting it looked
    # free; #43's task file omits it on purpose and the assertion was testing
    # our writing habits rather than the parser.
    #
    # The span-exactness check below is the guard that matters, and it now
    # covers all four section kinds rather than three. Findings cite requirement
    # text by position, so a span whose offsets do not reproduce its own text is
    # a wrong citation.
    for span in [
        *parsed.behavior,
        *parsed.constraints,
        *parsed.scope_exclusions,
        *parsed.completion_expectations,
    ]:
        assert parsed.source[span.start : span.end] == span.text


def test_a_bullet_wrapped_across_lines_still_has_an_exact_span():
    """Findings cite requirement text by position, so `source[start:end]` must
    equal `span.text` for every span — a citation that points a few characters
    off is a wrong citation.

    A wrapped bullet is the case that breaks it: markdown-it collapses the
    continuation line's indent, so the parser cannot find the content literally
    and falls back to the enclosing block. That fallback used to strip the text
    without narrowing the offsets, leaving the span one newline too long.
    """
    text = (
        "# Task\nDo the thing.\n\n"
        "## Constraints\n"
        "- A constraint long enough that it wraps onto a second\n"
        "  line with continuation indent.\n"
    )

    parsed = parse_task_file(text)

    (constraint,) = parsed.constraints
    assert parsed.source[constraint.start : constraint.end] == constraint.text
    assert constraint.text.endswith("continuation indent.")


# --- the parse must be complete before it can be authoritative (M1.2.r1) ----

MULTI_PARAGRAPH_TASK = """# Task
The tool drops requirements silently, and nobody notices.

Make it report what it dropped.

## Constraints
- Keep the existing output format.
"""


def test_every_paragraph_of_the_task_section_is_kept():
    """Keeping only the first cost nothing while the decomposer was handed
    `parsed.source` and read the file itself. It became silent data loss the
    moment M1.2.r1 made this parse the only thing the model sees — and the first
    casualty was the mandate sentence of the change that introduced it, which
    was the second paragraph."""
    parsed = parse_task_file(MULTI_PARAGRAPH_TASK)

    assert [b.text for b in parsed.behavior] == [
        "The tool drops requirements silently, and nobody notices.",
        "Make it report what it dropped.",
    ]


def test_text_outside_every_recognised_section_is_reported_not_dropped():
    task = """# Task
Do the thing.

## Background
This paragraph is under a heading the format does not recognise.

## Constraints
- Keep it fast.
"""
    parsed = parse_task_file(task)

    assert [b.text for b in parsed.behavior] == ["Do the thing."]
    assert [c.text for c in parsed.constraints] == ["Keep it fast."]
    assert [u.text for u in parsed.unclaimed] == [
        "This paragraph is under a heading the format does not recognise."
    ]


def test_a_table_no_section_claims_is_reported_whole():
    """`_span` locates a node's INLINE content, which for a table is its first
    cell — reporting that as the unread region would understate what was
    skipped. #195's own task file carries its ground truth in tables."""
    task = """# Task
Do the thing.

## Ground truth
| lost | at |
|---|---|
| the open-questions half | run 4 |
"""
    parsed = parse_task_file(task)

    assert len(parsed.unclaimed) == 1
    unread = parsed.unclaimed[0]
    assert "the open-questions half" in unread.text
    assert "| lost | at |" in unread.text
    # The span invariant still holds, so a citation into it points at real text.
    assert parsed.source[unread.start : unread.end] == unread.text


def test_a_fully_recognised_file_reports_nothing_unclaimed():
    assert parse_task_file(MULTI_PARAGRAPH_TASK).unclaimed == []
