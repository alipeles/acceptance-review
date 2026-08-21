"""Shared prompt-building for the M3 coverage analyses.

Both implementation-coverage classification (classify.py) and unrequested-change
detection (unrequested.py) present the same thing to the model — the obligations
and the diff with labeled hunks — and map the model's hunk labels back to
`DiffRef`s. That shared machinery lives here so the two modules don't reach into
each other's internals.
"""

from __future__ import annotations

from acceptance.model_base import PersistableModel
from acceptance.request_blocks import Block, BlockKind
from acceptance.review_state import ChangeSet, Obligation


class DiffRef(PersistableModel):
    """A link to a specific changed region (file + hunk header)."""

    file: str
    hunk_header: str


def hunk_label(path: str, index: int) -> str:
    return f"{path}#{index}"


def hunk_labels(change_set: ChangeSet) -> dict[str, DiffRef]:
    """Map each `path#index` label to the DiffRef it identifies."""
    labels: dict[str, DiffRef] = {}
    for file_change in change_set.files:
        for index, hunk in enumerate(file_change.hunks):
            labels[hunk_label(file_change.path, index)] = DiffRef(
                file=file_change.path, hunk_header=hunk.header
            )
    return labels


def render_diff_section(change_set: ChangeSet) -> list[str]:
    """The `## Diff` block (labeled hunks), shared by every prompt that shows
    the model a diff — factored out so each caller only supplies what comes
    before it (obligations, open questions, ...)."""
    lines = ["## Diff"]
    if not change_set.files:
        lines.append("(no changes)")
    for file_change in change_set.files:
        lines.append("")
        lines.append(f"### {file_change.path} ({file_change.status}, {file_change.category})")
        if not file_change.hunks:
            lines.append("(no hunks)")
        for index, hunk in enumerate(file_change.hunks):
            lines.append(f"[{hunk_label(file_change.path, index)}] {hunk.header}")
            lines.append(hunk.content)
    return lines


def diff_block(change_set: ChangeSet) -> Block:
    """The `## Diff` block, as the one string every stage that shows a diff uses.

    Five stages carry this and a provider reuses a repeated opening only when it
    is repeated *exactly*, so the value of routing them all through one function
    is byte-identity, not tidiness. A stage that rendered the same hunks with its
    own spacing would produce a block that looks the same to a reader and shares
    no prefix with the others.

    Rendering that is deliberately **not** shared: `evidence/discrimination.py`
    shows source files only, without hunk labels. That is a different view of the
    change, not a different formatting of this one, and unifying them would
    change what that stage is shown.
    """
    return Block(BlockKind.DIFF, "\n".join(render_diff_section(change_set)))


def obligations_block(obligations: list[Obligation]) -> Block:
    """The `## Obligations` list, shared by coverage classification and
    unrequested-change detection.

    The two stages pass different obligation sets on some runs — classification
    is given only the obligations it must classify — so this is one renderer
    producing one block *kind*, not a guarantee that the bytes match. When the
    sets do coincide the blocks are equal and the prefix is shared; when they do
    not, the diff above them is still shared, which is the larger half.
    """
    lines = ["## Obligations", ""]
    for obligation in obligations:
        lines.append(f"- id={obligation.id} [{obligation.type.value}]: {obligation.description}")
    return Block(BlockKind.OBLIGATIONS, "\n".join(lines))


def resolve_refs(labels: list[str], label_to_ref: dict[str, DiffRef]) -> list[DiffRef]:
    """Map returned hunk labels back to DiffRefs, dropping unknown labels."""
    return [label_to_ref[label] for label in labels if label in label_to_ref]
