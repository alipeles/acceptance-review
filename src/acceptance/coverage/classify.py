"""Obligation-to-diff classification (M3.1, §9.2 implementation-coverage review).

Classifies each obligation against the diff: does the changed code contain a
credible response to it? This is IMPLEMENTATION coverage only — it finds likely
incompleteness before acceptance; it does NOT prove the obligation works. That
is a separate axis: discriminating passing-test evidence (M4/M5, graded by the
§9.3 evidence classes and §8.1 evidence tiers). "Addressed" here means "the
code addresses it", never "the obligation is satisfied". It is also distinct
from M8's execution coverage (whether a test reaches the code).

Classification is a semantic judgment, so it is a schema-constrained model call
through the M0.4 harness — recorded for replay, never a live call in tests.
Each result links to the exact diff hunks that address the obligation, or
records that none do (empty diff_refs = "no corresponding change").
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from acceptance.llm import ModelClient
from acceptance.model_base import PersistableModel
from acceptance.review_state import ChangeSet, Obligation


class CoverageStatus(str, Enum):
    """§9.2 implementation-coverage classifications."""

    ADDRESSED = "addressed"
    PARTIALLY_ADDRESSED = "partially_addressed"
    NOT_ADDRESSED = "not_addressed"
    UNCLEAR = "unclear"
    REQUIRES_NON_CODE_EVIDENCE = "requires_non_code_evidence"


class DiffRef(PersistableModel):
    """A link to a specific changed region (file + hunk header)."""

    file: str
    hunk_header: str


class ImplementationCoverage(PersistableModel):
    """How the diff covers one obligation (implementation only, not test evidence)."""

    obligation_id: str
    status: CoverageStatus
    rationale: str
    diff_refs: list[DiffRef] = Field(default_factory=list)


_SYSTEM_PROMPT = """\
You classify how a code diff addresses each acceptance obligation. This is
IMPLEMENTATION coverage only — whether the changed code responds to the
obligation. Do NOT judge whether it is tested or correct; that is assessed
separately.

For each obligation return a `status`:
- addressed: the diff contains a credible, complete code response.
- partially_addressed: relevant behavior is present in the diff but a
  qualifier, branch, condition, or case is missing.
- not_addressed: no diff region responds to the obligation at all.
- unclear: the change may be indirect and static evidence is insufficient.
- requires_non_code_evidence: satisfying it needs docs, visual behavior, or
  deploy config rather than code.

Also return a short `rationale` and `diff_refs`: the labels (like `path#0`) of
the hunks that address the obligation. For not_addressed, `diff_refs` MUST be
empty. Link only hunks that genuinely respond to the obligation."""


class _Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligation_id: str
    status: CoverageStatus
    rationale: str
    diff_refs: list[str]


class _Coverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classifications: list[_Classification]


def classify_coverage(
    obligations: list[Obligation], change_set: ChangeSet, client: ModelClient
) -> list[ImplementationCoverage]:
    """Classify each obligation against the change set (implementation coverage)."""
    label_to_ref = _hunk_labels(change_set)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _render_prompt(obligations, change_set, label_to_ref)},
    ]
    result = client.complete(messages, _Coverage)

    by_id = {c.obligation_id: c for c in result.classifications}
    coverages = []
    for obligation in obligations:
        classification = by_id.get(obligation.id)
        if classification is None:
            coverages.append(
                ImplementationCoverage(
                    obligation_id=obligation.id,
                    status=CoverageStatus.UNCLEAR,
                    rationale="No classification was returned for this obligation.",
                )
            )
            continue
        refs = [label_to_ref[label] for label in classification.diff_refs if label in label_to_ref]
        coverages.append(
            ImplementationCoverage(
                obligation_id=obligation.id,
                status=classification.status,
                rationale=classification.rationale,
                diff_refs=refs,
            )
        )
    return coverages


def _hunk_labels(change_set: ChangeSet) -> dict[str, DiffRef]:
    labels: dict[str, DiffRef] = {}
    for file_change in change_set.files:
        for index, hunk in enumerate(file_change.hunks):
            labels[f"{file_change.path}#{index}"] = DiffRef(
                file=file_change.path, hunk_header=hunk.header
            )
    return labels


def _render_prompt(
    obligations: list[Obligation], change_set: ChangeSet, label_to_ref: dict[str, DiffRef]
) -> str:
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
            lines.append(f"[{file_change.path}#{index}] {hunk.header}")
            lines.append(hunk.content)
    return "\n".join(lines)
