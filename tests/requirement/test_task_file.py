from acceptance.requirement.task_file import ParsedTaskFile, parse_task_file

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

    assert parsed.behavior.text == "Add support for indirect circular references."
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

    spans = [parsed.behavior, *parsed.constraints, *parsed.completion_expectations]
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
    assert parsed.behavior.text == "Just a behavior, nothing else."
    assert parsed.constraints == []
    assert parsed.completion_expectations == []
    assert parsed.scope_exclusions == []


def test_roundtrips_through_persistence():
    parsed = parse_task_file(SPEC_EXAMPLE)
    assert ParsedTaskFile.from_dict(parsed.to_dict()) == parsed


def test_parses_the_projects_own_current_task_file():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    parsed = parse_task_file((repo_root / "current-task.md").read_text())

    assert parsed.behavior is not None
    assert parsed.constraints  # the dogfooded task lists constraints
    assert parsed.completion_expectations
    for span in [parsed.behavior, *parsed.constraints, *parsed.completion_expectations]:
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
