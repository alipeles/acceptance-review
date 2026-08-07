"""Region-level total coverage of the parse (#216, DR-216).

The parse is authoritative — it is the only thing the decomposer sees — so it
may only be trusted if it accounts for everything. #202 established that with
`unread_source`. #216 found the case where the guard reports zero while three
requirements are gone: they were inside a *claimed* list item, so they reached
neither a field nor `unclaimed`, and nothing existed to report.

These tests assert coverage over source regions rather than over a requirement
count, because a count is exactly what failed to notice.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import parse_task_file
from acceptance.source_ref import TextSpan

from tests.requirement.region_coverage import assert_total_region_coverage, uncovered_regions

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "nested-blocks"

_SECTION_FIELDS = (
    "behavior",
    "constraints",
    "scope_exclusions",
    "completion_expectations",
    "unclaimed",
)

# The reproduction from #216, verbatim.
REPRODUCTION = (FIXTURES / "nested-bullets.md").read_text()


def _fixture_files() -> list[Path]:
    return sorted(p for p in FIXTURES.glob("*.md") if p.name != "README.md")


def _committed_task_files() -> list[Path]:
    """The repository's own task files: the one in flight and every dogfood
    run's committed input."""
    files = [REPO_ROOT / "current-task.md"]
    files.extend(sorted(REPO_ROOT.glob("dogfood-logs/*/current-task.md")))
    return [f for f in files if f.is_file()]


def _decompose_stability_files() -> list[Path]:
    corpus = REPO_ROOT / "tests" / "fixtures" / "decompose-stability"
    return sorted(corpus.glob("*/current-task.md"))


def _has_nested_blocks(text: str) -> bool:
    """Whether any list item holds more than its own single paragraph.

    This is the construct the pre-#216 parser dropped: `_inline_content`
    returned the item's first inline node and stopped, so a second block inside
    the item was never visited.
    """
    for node in SyntaxTreeNode(MarkdownIt().parse(text)).walk():
        if node.type == "list_item" and len(node.children) > 1:
            return True
    return False


# --- the reproduction -------------------------------------------------------


def test_the_reproduction_yields_five_requirements():
    """#216's Acceptance: five requirements, or two plus three unread blocks.

    DR-216 decision 2 settles it as five — nested content gets its own
    requirement rather than widening its parent's span, because an absorbed
    requirement is silent and unrecoverable while a redundant one is noisy and
    merged downstream by #144.

    Asserted through `build_registry` rather than over `parsed.constraints`,
    because the id is what the decomposer is asked to account for: a span with
    no requirement id is not something the model can be held to.
    """
    parsed = parse_task_file(REPRODUCTION)
    registry = build_registry(parsed)

    constraints = [r for r in registry if r.id.startswith("constraint-")]
    assert [r.span.text for r in constraints] == [
        "The outer requirement.",
        "A nested requirement that is real.",
        "Another nested one.",
        "A second outer requirement.",
        "A second paragraph inside that same bullet, stating a further requirement.",
    ]
    # Document order, so the ids sort the way the file reads.
    assert [r.id for r in constraints] == [
        "constraint-01",
        "constraint-02",
        "constraint-03",
        "constraint-04",
        "constraint-05",
    ]


def test_the_reproduction_leaves_nothing_unaccounted_for():
    assert_total_region_coverage(REPRODUCTION, "#216 reproduction")


def test_every_requirement_of_the_reproduction_keeps_an_exact_span():
    """A nested requirement is a requirement, so findings cite it by position
    like any other: `source[start:end] == span.text` has to hold for it too."""
    parsed = parse_task_file(REPRODUCTION)
    for ref in build_registry(parsed):
        assert parsed.source[ref.span.start : ref.span.end] == ref.span.text


def test_a_list_item_with_a_nested_bullet_list_contributes_no_unaccounted_region():
    task = "# Task\nDo it.\n\n## Constraints\n- Outer.\n  - Nested.\n"

    assert uncovered_regions(task) == []
    assert [c.text for c in parse_task_file(task).constraints] == ["Outer.", "Nested."]


def test_a_list_item_with_two_paragraphs_contributes_no_unaccounted_region():
    task = "# Task\nDo it.\n\n## Constraints\n- First paragraph.\n\n  Second paragraph.\n"

    assert uncovered_regions(task) == []
    assert [c.text for c in parse_task_file(task).constraints] == [
        "First paragraph.",
        "Second paragraph.",
    ]


def test_a_dropped_region_is_detected_when_the_requirement_count_is_unchanged():
    """The assertion is over source regions, not over a requirement count —
    and this is the case that tells the two apart.

    A count cannot detect its own missing entries. That is not a theoretical
    objection: #216 shipped with a registry of the right shape, an empty
    `unclaimed`, and three requirements gone. So the coverage check has to
    survive a parse whose count is exactly right and whose spans are not.

    Here every span is present and the count is untouched; one span merely
    stops short of the text it claims. A count-based check sees nothing. This
    one names the characters that fell out.
    """
    text = "# Task\nDo it.\n\n## Constraints\n- Outer.\n  - Nested.\n"
    parsed = parse_task_file(text)
    assert uncovered_regions(text, parsed) == []

    damaged = parsed.model_copy(deep=True)
    whole = damaged.constraints[1]
    damaged.constraints[1] = TextSpan(
        text=whole.text[:3],
        start=whole.start,
        end=whole.start + 3,
    )

    # Same number of requirements in every section — a count is unmoved.
    assert len(damaged.constraints) == len(parsed.constraints)
    assert [len(getattr(damaged, f)) for f in _SECTION_FIELDS] == [
        len(getattr(parsed, f)) for f in _SECTION_FIELDS
    ]
    # The region check is not.
    assert [run for _, run in uncovered_regions(text, damaged)] == ["ted."]


# --- total coverage over corpora -------------------------------------------


@pytest.mark.parametrize("path", _fixture_files(), ids=lambda p: p.name)
def test_purpose_built_fixtures_are_fully_covered(path: Path):
    assert_total_region_coverage(path.read_text(), str(path.relative_to(REPO_ROOT)))


@pytest.mark.parametrize("path", _committed_task_files(), ids=lambda p: str(p))
def test_the_repositorys_own_task_files_are_fully_covered(path: Path):
    """#216's Acceptance names this corpus. It is a regression guard, not
    evidence the guard works — see the vacuity test below."""
    assert_total_region_coverage(path.read_text(), str(path.relative_to(REPO_ROOT)))


@pytest.mark.parametrize("path", _decompose_stability_files(), ids=lambda p: p.parent.name)
def test_the_decompose_stability_corpus_is_fully_covered(path: Path):
    assert_total_region_coverage(path.read_text(), str(path.relative_to(REPO_ROOT)))


# --- the fixtures must be able to fail (DR-216 decision 5) ------------------


@pytest.mark.parametrize("path", _fixture_files(), ids=lambda p: p.name)
def test_each_purpose_built_fixture_actually_exercises_nesting(path: Path):
    """Without this, the coverage tests above could all be vacuous.

    The repository's real task files contain no nested blocks at all, so
    running the assertion over them alone is green on a corpus that cannot
    fail it — the same shape of hole #216 exists to close. Each fixture must
    therefore contain the construct the pre-#216 parser dropped.
    """
    assert _has_nested_blocks(path.read_text()), (
        f"{path.name} contains no list item with nested blocks, so it cannot "
        f"distinguish the fixed parser from the one #216 reports"
    )


def test_the_corpora_under_test_are_not_empty():
    """A glob that matches nothing turns every parametrised test above into
    zero tests, which reports as a pass."""
    assert _fixture_files()
    assert _committed_task_files()
    assert _decompose_stability_files()


# --- the guard still reports what it could not read ------------------------


def test_nested_content_under_an_unrecognised_heading_is_reported_as_unread():
    """Coverage is satisfied by a registry span *or* an unclaimed span. Under a
    heading no §7.1 section claims, nested bullets take the second route — and
    the unaccounted-for count is non-zero, which is the guard working."""
    task = """# Task
Do the thing.

## Background
- An unclaimed outer note.
  - An unclaimed nested note.

## Constraints
- Keep it fast.
"""
    parsed = parse_task_file(task)

    assert [c.text for c in parsed.constraints] == ["Keep it fast."]
    assert [u.text for u in parsed.unclaimed] == [
        "An unclaimed outer note.",
        "An unclaimed nested note.",
    ]
    assert uncovered_regions(task) == []


def test_a_nested_fence_is_accounted_for_whole():
    """DR-216 decision 3: the parser never judges block type. A nested fence is
    not ruled illustrative here — it becomes an accountable block, and whether
    it states a requirement is the decomposer's call."""
    parsed = parse_task_file((FIXTURES / "nested-fence.md").read_text())

    fences = [c for c in parsed.constraints if c.text.startswith("```")]
    assert len(fences) == 1
    assert "assert source[span.start : span.end] == span.text" in fences[0].text
    # Spanned whole, not by its first inline line.
    assert fences[0].text.endswith("```")


def test_a_nested_table_is_accounted_for_whole():
    parsed = parse_task_file((FIXTURES / "nested-table.md").read_text())

    tables = [c for c in parsed.constraints if c.text.startswith("| tier |")]
    assert len(tables) == 1
    # `_span` would have reported a table's first cell; the whole block is what
    # was actually not read into a field.
    assert "| defect-killed | mutation runs |" in tables[0].text
