"""Task-file ingestion (M1.1, §7.1).

Parses the local task file (`current-task.md`) into structured fields — the
task behavior, its constraints, scope exclusions, and completion expectations —
each carrying a `TextSpan` back to the exact source it came from. Preserving
that source reference is the CLAUDE.md invariant that findings link to exact
requirement text: every later obligation (M1.2+) traces through these spans to
the words in the task file.

Markdown is parsed with markdown-it-py rather than a bespoke reader, since the
checker will eventually ingest richer user documents than the §7.1 shape.
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from acceptance.model_base import PersistableModel
from acceptance.source_ref import TextSpan

__all__ = ["TextSpan", "ParsedTaskFile", "parse_task_file"]

# §7.1 section headings, normalized (lowercased). A file may add other
# sections; unknown ones are ignored rather than rejected.
_CONSTRAINTS = {"constraints"}
_COMPLETION = {"completion expectations"}
_EXCLUSIONS = {"scope exclusions", "exclusions"}
_TASK = {"task"}


class ParsedTaskFile(PersistableModel):
    """The §7.1 task file parsed into fields, each linked to its source span.

    `behavior` is a LIST because the Task section routinely runs to several
    paragraphs. It used to keep only the first, which cost nothing while the
    decomposer was handed `parsed.source` and read the file itself — and became
    silent data loss the moment M1.2.r1 made this parse the only thing the model
    sees. A lossy parse is safe exactly until it is authoritative.

    `unclaimed` is every content block this parse did not route into a field:
    text under an unrecognised heading, tables, code fences, block quotes. It is
    recorded rather than discarded for the same reason a requirement yielding no
    obligation is recorded rather than dropped — the parse cannot be trusted to
    be complete, so it has to say what it did not take.
    """

    source: str
    behavior: list[TextSpan] = []
    constraints: list[TextSpan] = []
    scope_exclusions: list[TextSpan] = []
    completion_expectations: list[TextSpan] = []
    unclaimed: list[TextSpan] = []


def parse_task_file(text: str) -> ParsedTaskFile:
    line_offsets = _line_offsets(text)
    tree = SyntaxTreeNode(MarkdownIt().parse(text))

    result = ParsedTaskFile(source=text)
    section: str | None = None

    for node in tree.children:
        if node.type == "heading":
            # Headings are structure, not requirements, and are never unclaimed.
            section = _inline_content(node).strip().lower()
        elif node.type == "paragraph":
            target = result.behavior if section in _TASK else result.unclaimed
            target.append(_span(text, line_offsets, node))
        elif node.type == "bullet_list":
            target = _list_target(result, section)
            spans = [_span(text, line_offsets, item) for item in node.children]
            (result.unclaimed if target is None else target).extend(spans)
        else:
            # Tables, fenced code, block quotes. Nothing reads them yet — the
            # ground-truth tables in #195's own task file are invisible to this
            # parse — so the honest output is to say they were not read.
            result.unclaimed.append(_block_span(text, line_offsets, node))

    return result


def _list_target(result: ParsedTaskFile, section: str | None) -> list[TextSpan] | None:
    if section in _CONSTRAINTS:
        return result.constraints
    if section in _COMPLETION:
        return result.completion_expectations
    if section in _EXCLUSIONS:
        return result.scope_exclusions
    return None


def _line_offsets(text: str) -> list[int]:
    """Character offset of the start of each line (line k -> offsets[k])."""
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def _inline_content(node: SyntaxTreeNode) -> str:
    """The raw inline text of a heading / paragraph / list-item node."""
    if node.type == "inline":
        return node.content
    for child in node.children:
        found = _inline_content(child)
        if found:
            return found
    return ""


def _block_span(text: str, line_offsets: list[int], node: SyntaxTreeNode) -> TextSpan:
    """The whole of a block, with offsets narrowed to its stripped text.

    Used for blocks nothing parses into a field. `_span` locates a node's
    *inline* content, which for a table is its first cell — reporting that as
    the unread region would understate what was skipped.
    """
    start_line, end_line = node.map
    block_start = line_offsets[start_line]
    block_end = line_offsets[end_line] if end_line < len(line_offsets) else len(text)
    block = text[block_start:block_end]
    leading = len(block) - len(block.lstrip())
    trailing = len(block) - len(block.rstrip())
    return TextSpan(
        text=block.strip(),
        start=block_start + leading,
        end=block_end - trailing,
    )


def _span(text: str, line_offsets: list[int], node: SyntaxTreeNode) -> TextSpan:
    """Locate a node's inline content in the source and record its exact span.

    Uses the node's line map to bound the search so repeated phrases resolve to
    the right occurrence; the recorded span satisfies text[start:end] == content.
    """
    content = _inline_content(node)
    start_line, end_line = node.map
    block_start = line_offsets[start_line]
    block_end = line_offsets[end_line] if end_line < len(line_offsets) else len(text)

    offset = text.find(content, block_start, block_end)
    if offset < 0:
        # Content was normalized and is not literally present — a bullet wrapped
        # across lines has its continuation indent collapsed, so the search
        # misses. Fall back to the whole block, but narrow the OFFSETS to match
        # the stripped text rather than stripping only the text: findings cite
        # requirement spans by position, so `text[start:end] == span.text` has
        # to hold or a citation points at the wrong characters.
        block = text[block_start:block_end]
        leading = len(block) - len(block.lstrip())
        trailing = len(block) - len(block.rstrip())
        return TextSpan(
            text=block.strip(),
            start=block_start + leading,
            end=block_end - trailing,
        )
    return TextSpan(text=content, start=offset, end=offset + len(content))
