"""The four mechanical checks, and the region resolution they check against.

DR-171 Decision 3 as revised: validity is decided without a model call, and the
parse check applies only where there is a parser. The cases that matter most are
the two the revision changed — a non-Python file is mutable, and containment is
what keeps a mutant inside the defect it belongs to.
"""

from __future__ import annotations

import pytest

from acceptance.mutation.attempt import MutationDescriptor
from acceptance.mutation.region import Region, regions_for
from acceptance.mutation.validity import apply_span, invalidity_reason
from acceptance.review_state import ChangeSet, Defect, DefectType, DiffHunk, FileChange

PY_SOURCE = "def total(items):\n    return sum(items)\n\n\ndef half(value):\n    return value / 2\n"


def _region(path: str, start: int, end: int, label: str = "src.py#0") -> Region:
    return Region(label=label, path=path, start_line=start, end_line=end)


def _descriptor(**overrides) -> MutationDescriptor:
    fields = {
        "path": "src.py",
        "start_line": 2,
        "end_line": 2,
        "replacement": "    return sum(items) + 1\n",
        "region_label": "src.py#0",
    }
    fields.update(overrides)
    return MutationDescriptor(**fields)


class TestApplySpan:
    def test_replaces_exactly_the_named_lines(self):
        result = apply_span(PY_SOURCE, _descriptor())
        assert result.splitlines()[1] == "    return sum(items) + 1"
        # The untouched half of the file survives byte for byte.
        assert result.splitlines()[5] == "    return value / 2"

    def test_an_empty_replacement_deletes_the_span(self):
        result = apply_span(PY_SOURCE, _descriptor(replacement=""))
        assert "return sum(items)" not in result
        assert "def total(items):" in result

    def test_a_multi_line_span_collapses_to_the_replacement(self):
        result = apply_span(
            PY_SOURCE,
            _descriptor(start_line=1, end_line=2, replacement="def total(items):\n    return 0\n"),
        )
        assert result.startswith("def total(items):\n    return 0\n")
        assert "def half(value):" in result


class TestValidity:
    def test_a_contained_parsing_edit_is_valid(self):
        assert invalidity_reason(_descriptor(), [_region("src.py", 1, 3)], PY_SOURCE) is None

    def test_an_edit_outside_the_named_region_is_refused(self):
        # The defect named lines 1..3; the edit lands on line 6.
        reason = invalidity_reason(
            _descriptor(start_line=6, end_line=6, replacement="    return value\n"),
            [_region("src.py", 1, 3)],
            PY_SOURCE,
        )
        assert reason is not None
        assert "outside the region" in reason

    def test_an_edit_in_a_file_the_defect_never_named_is_refused(self):
        reason = invalidity_reason(
            _descriptor(path="other.py"), [_region("src.py", 1, 3)], PY_SOURCE
        )
        assert reason is not None
        assert "names no region in other.py" in reason

    def test_a_span_past_the_end_of_the_file_is_refused(self):
        reason = invalidity_reason(
            _descriptor(start_line=40, end_line=41),
            [_region("src.py", 1, 99)],
            PY_SOURCE,
        )
        assert reason is not None
        assert "runs past the end" in reason

    def test_an_edit_byte_identical_to_its_input_is_refused(self):
        """Nothing is injected, so every test would 'survive' a defect that was
        never introduced — a false finding against the builder. 21 of 71 edits
        on `gpt-5.4-mini` were this."""
        reason = invalidity_reason(
            _descriptor(replacement="    return sum(items)\n"),
            [_region("src.py", 1, 3)],
            PY_SOURCE,
        )
        assert reason is not None
        assert "identical to what it replaces" in reason

    def test_an_edit_differing_only_in_whitespace_is_not_identical(self):
        """Byte-identical means byte-identical. A whitespace change in Python
        can change behaviour, so it is left to the other checks."""
        reason = invalidity_reason(
            _descriptor(replacement="    return  sum(items)\n"),
            [_region("src.py", 1, 3)],
            PY_SOURCE,
        )
        assert reason is None or "identical" not in reason

    def test_an_oversized_edit_is_refused(self):
        reason = invalidity_reason(
            _descriptor(start_line=1, end_line=6, replacement="x = 1\n"),
            [_region("src.py", 1, 6)],
            PY_SOURCE,
            max_edit_lines=3,
        )
        assert reason is not None
        assert "over the 3-line bound" in reason

    def test_an_edit_that_breaks_python_syntax_is_refused(self):
        reason = invalidity_reason(
            _descriptor(replacement="    return sum(items\n"),
            [_region("src.py", 1, 3)],
            PY_SOURCE,
        )
        assert reason is not None
        assert "does not parse" in reason


class TestFilesWithoutAParser:
    """DR-171 Decision 3's 2026-09-14 revision.

    The original check ran `ast.parse` on every mutated file, which failed
    closed on anything Python cannot read and made every documentation defect
    unmutable. These two cases are the revision.
    """

    MARKDOWN = "# Title\n\nThe budget defaults to 30 seconds.\n"

    def test_a_markdown_edit_is_valid(self):
        descriptor = MutationDescriptor(
            path="README.md",
            start_line=3,
            end_line=3,
            replacement="The budget defaults to 3000 seconds.\n",
            region_label="README.md#0",
        )
        assert invalidity_reason(descriptor, [_region("README.md", 1, 3)], self.MARKDOWN) is None

    def test_markdown_that_would_not_be_valid_python_is_still_valid(self):
        # The point of the revision: prose is not judged as code.
        descriptor = MutationDescriptor(
            path="README.md",
            start_line=3,
            end_line=3,
            replacement="def ( this is not python at all\n",
            region_label="README.md#0",
        )
        assert invalidity_reason(descriptor, [_region("README.md", 1, 3)], self.MARKDOWN) is None

    def test_a_json_file_that_stops_parsing_is_refused(self):
        """#45's Gate 2 found this gap. With only Python in the parser map, a
        mutated `.json` passed validity however malformed it was, while the
        requirement is that a file *that has a parser* still parses."""
        source = '{\n  "per_test_seconds": 30\n}\n'
        descriptor = MutationDescriptor(
            path="config.json",
            start_line=2,
            end_line=2,
            replacement='  "per_test_seconds": 30,,,\n',
            region_label="config.json#0",
        )
        reason = invalidity_reason(descriptor, [_region("config.json", 1, 3)], source)
        assert reason is not None
        assert "does not parse" in reason

    def test_a_json_file_that_still_parses_is_valid(self):
        """The parse check refuses malformed output, not every edit — otherwise
        a documentation or config defect could never be injected at all."""
        source = '{\n  "per_test_seconds": 30\n}\n'
        descriptor = MutationDescriptor(
            path="config.json",
            start_line=2,
            end_line=2,
            replacement='  "per_test_seconds": 3000\n',
            region_label="config.json#0",
        )
        assert invalidity_reason(descriptor, [_region("config.json", 1, 3)], source) is None

    def test_containment_still_applies_to_a_file_with_no_parser(self):
        """The check that carries validity once the parse check stops being
        universal. Without it a prose mutant could land anywhere."""
        descriptor = MutationDescriptor(
            path="README.md",
            start_line=1,
            end_line=1,
            replacement="# Other\n",
            region_label="README.md#0",
        )
        reason = invalidity_reason(descriptor, [_region("README.md", 2, 3)], self.MARKDOWN)
        assert reason is not None
        assert "outside the region" in reason


class TestRegionsFor:
    def _change_set(self, *, new_start: int = 10, new_lines: int = 4) -> ChangeSet:
        return ChangeSet(
            base_revision="a",
            head_revision="b",
            files=[
                FileChange(
                    path="src.py",
                    status="modified",
                    category="source",
                    hunks=[
                        DiffHunk(
                            header="@@",
                            old_start=10,
                            old_lines=2,
                            new_start=new_start,
                            new_lines=new_lines,
                            content="body",
                        )
                    ],
                )
            ],
        )

    def _defect(self, refs: list[str]) -> Defect:
        return Defect(
            id="d1",
            obligation_id="o1",
            type=DefectType.OTHER,
            description="d",
            code_refs=refs,
        )

    def test_a_named_hunk_becomes_an_inclusive_span_at_head(self):
        regions = regions_for(self._defect(["src.py#0"]), self._change_set())
        assert [(r.path, r.start_line, r.end_line) for r in regions] == [("src.py", 10, 13)]

    def test_a_label_naming_no_region_is_dropped(self):
        assert regions_for(self._defect(["src.py#7"]), self._change_set()) == []

    def test_a_defect_with_no_code_refs_has_no_region(self):
        """The absence classes land here: `not_wired`, `missing_case` and
        friends name no region because the defect is that the code is not
        there, so there is no span to replace."""
        assert regions_for(self._defect([]), self._change_set()) == []

    def test_a_deletion_only_hunk_yields_no_region(self):
        regions = regions_for(self._defect(["src.py#0"]), self._change_set(new_lines=0))
        assert regions == []


class TestRegionContains:
    @pytest.mark.parametrize(
        ("start", "end", "expected"),
        [
            (10, 13, True),  # exactly the region
            (11, 12, True),  # strictly inside
            (9, 13, False),  # starts before
            (10, 14, False),  # ends after
        ],
    )
    def test_boundaries(self, start: int, end: int, expected: bool):
        assert _region("src.py", 10, 13).contains(start, end) is expected
