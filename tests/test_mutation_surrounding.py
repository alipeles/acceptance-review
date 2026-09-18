"""Which retrieved context a mutation-stage call is shown, and how it reads."""

from __future__ import annotations

from acceptance.change.context import CallSite, CodeContext, CodeDefinition, RetrievalResult
from acceptance.mutation.surrounding import contexts_for, render_contexts


def _context(
    qualname: str, file: str, start: int, end: int, calls: list[CallSite] | None = None
) -> CodeContext:
    body = "\n".join(f"line {n}" for n in range(start, end + 1))
    return CodeContext(
        definition=CodeDefinition(
            qualname=qualname,
            kind="function",
            file=file,
            start_line=start,
            end_line=end,
            source=body,
        ),
        call_sites=calls or [],
    )


_RETRIEVAL = RetrievalResult(
    contexts=[
        _context("first", "a.py", 1, 10),
        _context("second", "a.py", 20, 30),
        _context("other", "b.py", 1, 10),
    ]
)


class TestSelection:
    def test_only_definitions_overlapping_a_span_are_chosen(self):
        chosen = contexts_for([("a.py", 22, 24)], _RETRIEVAL)
        assert [c.definition.qualname for c in chosen] == ["second"]

    def test_a_span_touching_a_definition_s_edge_counts(self):
        assert [c.definition.qualname for c in contexts_for([("a.py", 10, 12)], _RETRIEVAL)] == [
            "first"
        ]

    def test_the_file_must_match(self):
        assert contexts_for([("c.py", 1, 10)], _RETRIEVAL) == []

    def test_a_span_at_module_level_chooses_nothing(self):
        assert contexts_for([("a.py", 12, 18)], _RETRIEVAL) == []

    def test_no_retrieval_chooses_nothing(self):
        assert contexts_for([("a.py", 1, 10)], None) == []

    def test_call_sites_in_test_files_are_withheld(self):
        """The mutation stage stays blind to the tests, as enumeration is."""
        sites = [
            CallSite(file="src/app.py", line=3, source_line="first()"),
            CallSite(file="tests/test_a.py", line=9, source_line="first()"),
            CallSite(file="test_a.py", line=4, source_line="first()"),
        ]
        retrieval = RetrievalResult(contexts=[_context("first", "a.py", 1, 10, sites)])
        (chosen,) = contexts_for([("a.py", 1, 10)], retrieval)
        assert [site.file for site in chosen.call_sites] == ["src/app.py"]


class TestRendering:
    def test_the_definition_is_numbered_with_the_file_s_own_lines(self):
        text = render_contexts([_context("second", "a.py", 20, 21)])
        assert "function second — a.py lines 20-21" in text
        assert "20 | line 20" in text
        assert "21 | line 21" in text

    def test_call_sites_are_listed_with_where_they_are(self):
        site = CallSite(file="c.py", line=7, source_line="second(x)", in_definition="main")
        text = render_contexts([_context("second", "a.py", 20, 21, [site])])
        assert "- c.py:7 in main: second(x)" in text

    def test_no_caller_is_stated_rather_than_left_blank(self):
        assert "no in-repo call site found" in render_contexts([_context("x", "a.py", 1, 2)])

    def test_a_truncated_list_says_so(self):
        context = _context("x", "a.py", 1, 2).model_copy(update={"call_sites_truncated": True})
        assert "cut at the retrieval budget" in render_contexts([context])

    def test_nothing_to_show_renders_nothing(self):
        assert render_contexts([]) == ""
