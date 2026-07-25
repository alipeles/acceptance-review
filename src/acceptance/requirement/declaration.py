"""Builder declaration ingestion (M6.1, §7.4).

Parses an optional end-of-cycle builder declaration — the nine §7.4 template
sections, as raw text — when the reviewed change ships one. A declaration is
**optional by default** in local mode: when absent, the review proceeds in
full and a minor finding records the absence, rather than blocking or
degrading anything else (§7.4, "optional-by-default").

A declaration is "a claim, not proof" (§7.4) — `BuilderDeclaration` holds raw
text for a later capability (M6.2, #31) to compare against actual evidence;
parsing here does no comparison and makes no judgment about truthfulness. A
declaration may also be partial — informally omitting a section is not an
error, since §7.4 doesn't require every section be filled in; an omitted
section is recorded as an empty string, not rejected.

Markdown is parsed with markdown-it-py, the same approach `task_file.py`
(M1.1) uses, since both ingest a fixed-shape §7 template.
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.review_state import DECLARATION_ABSENT, BuilderDeclaration, Finding, Link

__all__ = ["parse_declaration", "declaration_absent_finding"]

# §7.4 template section headings, normalized (lowercased), to the
# BuilderDeclaration field each fills. A section a declaration omits is left
# as "" rather than rejected — a partial declaration is still a declaration.
_SECTIONS = {
    "mandate as understood": "mandate_as_understood",
    "implementation summary": "implementation_summary",
    "scope exclusions": "scope_exclusions",
    "assumptions": "assumptions",
    "changed components": "changed_components",
    "test evidence": "test_evidence",
    "regression evidence": "regression_evidence",
    "known limitations": "known_limitations",
    "additional behavioral changes": "additional_behavioral_changes",
}


def parse_declaration(text: str) -> BuilderDeclaration:
    """Parse a builder declaration's §7.4 sections from raw markdown text."""
    tree = SyntaxTreeNode(MarkdownIt().parse(text))
    content_by_field: dict[str, str] = {}
    field: str | None = None

    for node in tree.children:
        if node.type == "heading":
            field = _SECTIONS.get(_inline_content(node).strip().lower())
            continue
        if field is None:
            continue
        block = _block_text(node)
        if not block:
            continue
        existing = content_by_field.get(field, "")
        content_by_field[field] = f"{existing}\n\n{block}" if existing else block

    return BuilderDeclaration(**{name: content_by_field.get(name, "") for name in _SECTIONS.values()})


def _inline_content(node: SyntaxTreeNode) -> str:
    """The raw inline text of a heading / paragraph / list-item node."""
    if node.type == "inline":
        return node.content
    for child in node.children:
        found = _inline_content(child)
        if found:
            return found
    return ""


def _block_text(node: SyntaxTreeNode) -> str:
    """Render a non-heading block (paragraph, bullet/ordered list, ...) to
    plain text for a declaration section — declaration content is prose or a
    short list, not code requiring exact formatting preservation."""
    if node.type in ("bullet_list", "ordered_list"):
        return "\n".join(f"- {_block_text(item)}" for item in node.children)
    if node.type == "list_item":
        return "\n".join(_block_text(child) for child in node.children if _block_text(child)).strip()
    return _inline_content(node)


def declaration_absent_finding() -> Finding:
    """§7.4: when no declaration is present, a full review proceeds and its
    absence is recorded as a minor finding — not a blocker, not silence."""
    return Finding(
        type=DECLARATION_ABSENT,
        severity="low",
        description=(
            "No builder declaration was supplied for this review. §7.4 treats "
            "a declaration as optional by default in local mode; the review "
            "proceeds in full without one."
        ),
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="declaration", ref="declaration", text="no declaration was provided")],
    )
