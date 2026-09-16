"""The surrounding code a mutation-stage call is shown, beyond the named lines.

The edit-building call used to see only the changed lines a defect names. On
#45's own review that blind spot showed up directly: edits that crashed because
the lines just past the region were never shown, "already present" claims about
routing that lives in another module, and edits that changed nothing a caller
could observe. The verifier's "cannot tell" refusals were about code outside its
window too.

The fix is the bounded context the product already retrieves for M2.2
(`change/context.py`): each changed region's enclosing definition and its direct
in-repo call sites. Not whole files — those change how much the call sees as
well as what, overrun the budget on a large module, and make every request
unique. This module picks the part of that retrieval a defect's regions fall
in, and renders it the same way for every call that uses it.
"""

from __future__ import annotations

from collections.abc import Sequence

from acceptance.change.context import CodeContext, RetrievalResult
from acceptance.change.diff import is_test_path
from acceptance.mutation.region import Region

__all__ = ["contexts_for", "region_spans", "render_contexts"]


def contexts_for(
    spans: Sequence[tuple[str, int, int]], retrieval: RetrievalResult | None
) -> list[CodeContext]:
    """The retrieved contexts whose enclosing definition overlaps any span.

    Each span is `(path, start_line, end_line)`, 1-based and inclusive. A span at
    module level has no enclosing definition and picks nothing, which is the
    retrieval's own limit rather than a gap here. Order follows the retrieval, so
    the same inputs render the same text.
    """
    if retrieval is None:
        return []
    chosen: list[CodeContext] = []
    for context in retrieval.contexts:
        definition = context.definition
        if any(
            path == definition.file
            and start <= definition.end_line
            and definition.start_line <= end
            for path, start, end in spans
        ):
            chosen.append(_without_tests(context))
    return chosen


def _without_tests(context: CodeContext) -> CodeContext:
    """`context` with every call site inside a test file removed.

    The retrieval finds callers wherever they are, and the tests are callers. A
    call that builds an edit while reading the tests can aim it at what they do
    or do not catch; a call that verifies an edit while reading them can judge
    it by its outcome. Both would bias the very observation injection exists to
    make, so the tests are withheld here as the defect enumerator's are.
    """
    kept = [site for site in context.call_sites if not is_test_path(site.file)]
    if len(kept) == len(context.call_sites):
        return context
    return context.model_copy(update={"call_sites": kept})


def region_spans(regions: Sequence[Region]) -> list[tuple[str, int, int]]:
    return [(region.path, region.start_line, region.end_line) for region in regions]


def render_contexts(contexts: Sequence[CodeContext]) -> str:
    """The enclosing definitions with absolute line numbers, then their callers.

    Numbered with the file's own line numbers, as the named region lines are, so
    a model that reads a line here names the same line in its answer. Truncation
    is stated rather than hidden: a list of callers cut at the budget reads the
    same as a complete one otherwise.
    """
    if not contexts:
        return ""
    lines = ["## Surrounding code (enclosing definitions and their callers)"]
    for context in contexts:
        definition = context.definition
        lines.append("")
        lines.append(
            f"### {definition.kind} {definition.qualname} — {definition.file} "
            f"lines {definition.start_line}-{definition.end_line}"
        )
        width = len(str(definition.end_line))
        for offset, text in enumerate(definition.source.splitlines()):
            lines.append(f"{definition.start_line + offset:>{width}} | {text}")
        lines.append("")
        if context.call_sites:
            lines.append(f"Called from ({len(context.call_sites)}):")
            for site in context.call_sites:
                where = f" in {site.in_definition}" if site.in_definition else ""
                lines.append(f"- {site.file}:{site.line}{where}: {site.source_line}")
        else:
            lines.append("Called from: no in-repo call site found.")
        if context.call_sites_truncated:
            lines.append("(more call sites exist; the list was cut at the retrieval budget)")
    return "\n".join(lines)
