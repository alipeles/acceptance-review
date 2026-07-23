"""Unrequested-change detection (M3.2, §9.2).

The inverse of implementation-coverage classification (classify.py): instead of
asking "which diff region addresses this obligation", it asks "which diff
region does no obligation call for" and flags those as candidate unrequested
changes — giving extra weight to public-interface, dependency, and
adjacent-behavior changes, which are the ones most worth a human's attention
(§9.2, demonstration scenario #8).

A semantic judgment, so a schema-constrained model call through the M0.4
harness — recorded for replay, never a live call in tests. Each flagged change
links to the exact diff hunks it concerns.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from acceptance.coverage.prompt import DiffRef, hunk_labels, render_diff_prompt, resolve_refs
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.review_state import ChangeSet, Obligation


class UnrequestedChangeKind(str, Enum):
    PUBLIC_INTERFACE = "public_interface"
    DEPENDENCY = "dependency"
    ADJACENT_BEHAVIOR = "adjacent_behavior"
    INTERNAL = "internal"
    OTHER = "other"


class UnrequestedChange(PersistableModel):
    """A diff region no obligation called for (§9.2 unrequested change)."""

    kind: UnrequestedChangeKind
    rationale: str
    diff_refs: list[DiffRef] = Field(default_factory=list)


_SYSTEM_PROMPT = """\
You find UNREQUESTED changes: diff regions that no listed obligation calls for.
The obligations are the complete set of what the task asked for. Any change not
needed to satisfy some obligation is a candidate unrequested change — report it.

Give extra weight to (classify each `kind`):
- public_interface: a change to a public function/method signature, name, return
  type, or exported symbol.
- dependency: an added/removed/upgraded dependency or config that affects them.
- adjacent_behavior: a behavior change to code the task did not mention.
- internal: a purely internal refactor with no external effect.
- other: anything else unrequested.

Before reporting a change, check it against the FULL text of EVERY obligation.
An obligation may explicitly call for an ARTIFACT — a fixture, test, example, or
sample — whose content is deliberately meant to look like a change a reviewer
would question: a planted bug, an odd edit to existing code, a deprecated call,
an intentionally weak test. Content an obligation asked for AS such an artifact
is REQUESTED by that obligation, even though in isolation it resembles scope
creep — do NOT report it. Only report a change when NO obligation, read in full,
calls for it. (When you are genuinely unsure whether any obligation covers a
change, still report it — bias toward surfacing the unexplained.)

For each unrequested change return its `kind`, a short `rationale`, and
`diff_refs`: the labels (like `path#0`) of the hunks it concerns. Do not report
changes that a listed obligation requires. If every change is requested, return
an empty list."""


class _Detected(StrictResponseModel):
    kind: UnrequestedChangeKind
    rationale: str
    diff_refs: list[str]


class _Detections(StrictResponseModel):
    unrequested_changes: list[_Detected]


def detect_unrequested_changes(
    obligations: list[Obligation], change_set: ChangeSet, client: ModelClient
) -> list[UnrequestedChange]:
    """Flag diff regions no obligation calls for as candidate unrequested changes."""
    label_to_ref = hunk_labels(change_set)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": render_diff_prompt(obligations, change_set)},
    ]
    result = client.complete(messages, _Detections)

    changes = []
    for detected in result.unrequested_changes:
        refs = resolve_refs(detected.diff_refs, label_to_ref)
        changes.append(
            UnrequestedChange(kind=detected.kind, rationale=detected.rationale, diff_refs=refs)
        )
    return changes
