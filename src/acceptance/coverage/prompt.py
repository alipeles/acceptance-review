"""Shared prompt-building for the M3 coverage analyses.

Both implementation-coverage classification (classify.py) and unrequested-change
detection (unrequested.py) present the same thing to the model — the obligations
and the diff with labeled hunks — and map the model's hunk labels back to
`DiffRef`s. That shared machinery lives here so the two modules don't reach into
each other's internals.
"""

from __future__ import annotations

from acceptance.model_base import PersistableModel
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


def render_diff_prompt(obligations: list[Obligation], change_set: ChangeSet) -> str:
    """Render obligations + the labeled diff for the model to reason over."""
    lines = ["## Obligations", ""]
    for obligation in obligations:
        lines.append(f"- id={obligation.id} [{obligation.type.value}]: {obligation.description}")
    lines.append("")
    lines.append("## Diff")
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
    return "\n".join(lines)


def resolve_refs(labels: list[str], label_to_ref: dict[str, DiffRef]) -> list[DiffRef]:
    """Map returned hunk labels back to DiffRefs, dropping unknown labels."""
    return [label_to_ref[label] for label in labels if label in label_to_ref]
