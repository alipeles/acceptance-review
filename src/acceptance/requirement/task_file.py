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
from pydantic import Field

from acceptance.model_base import PersistableModel
from acceptance.source_ref import TextSpan

__all__ = ["ParsedTaskFile", "TextSpan", "parse_task_file"]

# §7.1 section headings, normalized (lowercased). A file may add other
# sections; unknown ones are ignored rather than rejected.
_CONSTRAINTS = {"constraints"}
_COMPLETION = {"completion expectations"}
_EXCLUSIONS = {"scope exclusions", "exclusions"}
_TASK = {"task"}

# Container nodes: they hold blocks rather than being one, so they are
# descended into rather than spanned. Spanning a container would double-count
# the blocks inside it, and — for a list item with nested content — is exactly
# the widening DR-216 decision 2 rejects.
_LISTS = {"bullet_list", "ordered_list"}


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

    The unit of all five lists is a **block** — an AST leaf, not a semantic
    requirement — and every non-whitespace, non-heading block of the file is
    inside one of them (DR-216 decision 1). That total-coverage property is what
    lets `unread_source` report zero and mean it; before #216 a block nested
    inside a claimed list item was in none of the five, so the zero was
    unfalsifiable. Finding the independent requirements *inside* a block is the
    decomposer's job, not this one's — see DR-216 for why that split is where it
    is, and #224 for what still goes unmeasured on the other side of it.
    """

    source: str
    behavior: list[TextSpan] = Field(default_factory=list)
    constraints: list[TextSpan] = Field(default_factory=list)
    scope_exclusions: list[TextSpan] = Field(default_factory=list)
    completion_expectations: list[TextSpan] = Field(default_factory=list)
    unclaimed: list[TextSpan] = Field(default_factory=list)


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
        elif node.type in _LISTS:
            target = _list_target(result, section)
            dest = result.unclaimed if target is None else target
            _emit_list(text, line_offsets, node, dest)
        else:
            # Tables, fenced code, block quotes. Nothing reads them yet — the
            # ground-truth tables in #195's own task file are invisible to this
            # parse — so the honest output is to say they were not read.
            result.unclaimed.append(_block_span(text, line_offsets, node))

    return result


def _emit_list(
    text: str, line_offsets: list[int], node: SyntaxTreeNode, dest: list[TextSpan]
) -> None:
    for item in node.children:
        _emit_item(text, line_offsets, item, dest)


def _emit_item(
    text: str, line_offsets: list[int], item: SyntaxTreeNode, dest: list[TextSpan]
) -> None:
    """Every block inside one list item, each as its own span (DR-216).

    A list item's children are blocks: its own paragraph, then whatever is
    nested under it — a further list, a second paragraph, a fence, a table.
    This used to span the item once via `_inline_content`, which returns the
    FIRST inline node it finds and stops. The narrow span was located in the
    source, so `_span`'s widening fallback never fired, and everything after
    that first paragraph reached neither a field nor `unclaimed`: no
    requirement id, no disposition, and — because the item was claimed —
    nothing for `unread_source` to report either (#216).

    Nested content becomes its own requirement rather than widening the
    parent's span, per DR-216 decision 2: a redundant requirement is noisy and
    recoverable, an absorbed one is silent and not. Block type is never judged
    (decision 3) — a nested fence and a nested bullet are treated alike, and
    what a block MEANS is the decomposer's judgment, not the parser's.
    """
    for child in item.children:
        if child.type in _LISTS:
            _emit_list(text, line_offsets, child, dest)
        elif child.type == "paragraph":
            dest.append(_span(text, line_offsets, child))
        else:
            dest.append(_block_span(text, line_offsets, child))


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
