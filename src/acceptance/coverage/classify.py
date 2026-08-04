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
from acceptance.supplied_ids import UnusableAnswerLog, constrain, scan
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


_STAGE = "coverage classification"

_SYSTEM_PROMPT = """\
You classify how a code diff addresses each acceptance obligation. This is
IMPLEMENTATION coverage only — whether the changed code responds to the
obligation. Do NOT judge whether it is tested or correct; that is assessed
separately.

For each obligation return a `status`:
- addressed: the evidence in the diff confirms the obligation is handled —
  either the diff contains a credible, complete code response, OR (for an
  obligation to PRESERVE or MAINTAIN an existing property — "keep X working",
  "preserve behavior Y", "keep the dependency set unchanged") the diff does
  not violate that property. A preserve/maintain obligation can be addressed
  with NO relevant change at all: if nothing in the diff touches or endangers
  the property, it is preserved — return `addressed` with empty `diff_refs`
  and a rationale saying the invariant is not violated. "Addressed" means the
  evidence was reviewed and the obligation is confirmed handled, not that a
  change was necessarily made for it.
- partially_addressed: relevant behavior is present in the diff but a
  qualifier, branch, condition, or case is missing; or a preserve/maintain
  obligation is only partly upheld.
- not_addressed: a positive obligation has no responding diff region, or a
  preserve/maintain obligation is clearly VIOLATED by the diff.
- unclear: the change may be indirect and static evidence is insufficient.
- requires_non_code_evidence: confirming it needs evidence the diff alone
  can't give — e.g. runtime behavior, visual output, or deploy config. (Some
  invariants, like a latency bound, CAN be confirmed by a suitable test; use
  this status only when no code-level evidence could settle it.)

Judge each region against the FULL text of the obligation, not against a fixed
idea of "correct production code." An obligation may ask for an ARTIFACT — a
fixture, test, example, sample, or data file — whose content is deliberately
meant to resemble something a reviewer would otherwise question: a planted bug,
an odd edit to existing code, a deprecated call, an intentionally weak test.
When an obligation calls for such an artifact and the diff delivers exactly
that content, it is `addressed` — judge it by whether it contains what the
obligation says the artifact should show, NOT by whether it is correct runtime
behavior. Each file is tagged `(status, category)`; treat a `test`-category
file as a deliverable artifact, not as production code held to correctness.

Also return a short `rationale` and `diff_refs`: the labels (like `path#0`) of
the hunks the status concerns. Link only hunks that genuinely bear on the
obligation. `diff_refs` is empty when there is nothing to point at — a
positive obligation that is not_addressed (no responding region), or a
preserve/maintain obligation that is addressed by the ABSENCE of any relevant
change. When a preserve/maintain obligation is not_addressed because the diff
VIOLATES it, cite the violating hunk(s) so a reviewer can see the breach."""


class _Classification(StrictResponseModel):
    obligation_id: str
    status: CoverageStatus
    rationale: str
    diff_refs: list[str]


class _Coverage(StrictResponseModel):
    classifications: list[_Classification]


def classify_coverage(
    obligations: list[Obligation],
    change_set: ChangeSet,
    client: ModelClient,
    unusable: UnusableAnswerLog | None = None,
) -> list[ImplementationCoverage]:
    """Classify each obligation against the change set (implementation coverage)."""
    label_to_ref = hunk_labels(change_set)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": render_diff_prompt(obligations, change_set)},
    ]
    allowed = {
        "obligation_id": [obligation.id for obligation in obligations],
        "diff_refs": list(label_to_ref),
    }
    result = client.complete(messages, constrain(_Coverage, allowed), parse_as=_Coverage)
    if unusable is not None:
        unusable.record(scan(result, allowed, _STAGE))

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
