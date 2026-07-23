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

from pydantic import Field

from acceptance.coverage.prompt import DiffRef, hunk_labels, render_diff_prompt, resolve_refs
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.review_state import ChangeSet, Obligation

__all__ = ["CoverageStatus", "DiffRef", "ImplementationCoverage", "classify_coverage"]


class CoverageStatus(str, Enum):
    """§9.2 implementation-coverage classifications."""

    ADDRESSED = "addressed"
    PARTIALLY_ADDRESSED = "partially_addressed"
    NOT_ADDRESSED = "not_addressed"
    UNCLEAR = "unclear"
    REQUIRES_NON_CODE_EVIDENCE = "requires_non_code_evidence"


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


class _Classification(StrictResponseModel):
    obligation_id: str
    status: CoverageStatus
    rationale: str
    diff_refs: list[str]


class _Coverage(StrictResponseModel):
    classifications: list[_Classification]


def classify_coverage(
    obligations: list[Obligation], change_set: ChangeSet, client: ModelClient
) -> list[ImplementationCoverage]:
    """Classify each obligation against the change set (implementation coverage)."""
    label_to_ref = hunk_labels(change_set)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": render_diff_prompt(obligations, change_set)},
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
        refs = resolve_refs(classification.diff_refs, label_to_ref)
        coverages.append(
            ImplementationCoverage(
                obligation_id=obligation.id,
                status=classification.status,
                rationale=classification.rationale,
                diff_refs=refs,
            )
        )
    return coverages
