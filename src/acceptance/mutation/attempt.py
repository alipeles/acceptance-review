"""What one injection attempt produced.

DR-171 Decision 8, as revised 2026-09-14. Every defect the mutation stage was
asked about ends with exactly one outcome, and the two outcomes that settle
nothing carry a reason — for the same reason `DefectSet` requires one on an
empty set and `TestOutcome` requires one on a test that did not complete:
"looked and could not" and "did not look" are different, and only one of them is
a defect in the tool.

The two settling outcomes both reach `DEFECT_KILLED`, because both were
observed. `killed` and `survived` are equally strong evidence; they disagree
about the tests, not about how well the answer is known.

The two non-settling outcomes are **routing instructions, not conclusions**. A
defect marked `not_mutable` or `not_attempted` has not been decided here; it is
handed to the static pair judgement, and the verdict that comes back is what the
rating uses.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from acceptance.evidence_tier import Component, EvidenceTier, authorize_tier
from acceptance.model_base import PersistableModel as _Model

__all__ = [
    "DECLINE_OUTCOMES",
    "SETTLING_KINDS",
    "DeclineKind",
    "DescriptorDecline",
    "MutationAttempt",
    "MutationDescriptor",
    "MutationOutcomeKind",
    "tier_for",
]


class MutationOutcomeKind(str, Enum):
    """The things that can become of a defect the stage was asked about.

    Three of them record why no mutant was built, and they are kept apart
    because each asks something different of the reader:

    - `already_present`: the descriptor stage said the delivered code already
      behaves the way the defect describes. That is a claim that the code is
      wrong, not that the tests are thin, so it is shown as needing human review.
    - `not_a_code_property`: the defect is not about what any span of code or
      text does — a question about the process, say — so no edit could settle it.
    - `not_mutable`: the defect is about code, but no single valid contiguous
      edit could be built for it. Also the outcome when a mechanical check
      refuses the edit, or the defect named no usable region.

    All three are routed to the static judge exactly as before; none moves a
    rating.
    """

    KILLED = "killed"
    SURVIVED = "survived"
    NOT_MUTABLE = "not_mutable"
    ALREADY_PRESENT = "already_present"
    NOT_A_CODE_PROPERTY = "not_a_code_property"
    NOT_ATTEMPTED = "not_attempted"


#: The kinds where execution actually decided the question. Only these may be
#: read as evidence about the tests; the other two say something about the run.
SETTLING_KINDS = frozenset({MutationOutcomeKind.KILLED, MutationOutcomeKind.SURVIVED})


def tier_for(kind: MutationOutcomeKind) -> EvidenceTier:
    """The evidence tier an outcome of `kind` reaches.

    Routed through `authorize_tier` rather than returned directly, so the
    ceiling this component is allowed to produce is enforced by the one place
    that owns it (CLAUDE.md's evidence-tier invariant) instead of being restated
    here where it could drift.
    """
    tier = EvidenceTier.DEFECT_KILLED if kind in SETTLING_KINDS else EvidenceTier.STATIC
    return authorize_tier(Component.MUTATION_RUNNER, tier)


class MutationDescriptor(_Model):
    """The edit that makes one named defect true.

    One contiguous span replacement in a single file (DR-171 Decision 2), where
    `start_line` and `end_line` are 1-based and inclusive. `replacement` is the
    text those lines become; an empty string deletes them.

    `region_label` records which of the defect's own `code_refs` the span falls
    inside, so the containment check's answer is stored rather than recomputed
    by anyone who later wants to know why this edit was allowed.

    `original` is the text the span held before the edit. It is stored because
    a replacement alone cannot show a deletion — an empty replacement renders as
    nothing — and a report reader has no other copy of the code as reviewed.
    Defaulted, so a review recorded before it existed reads back unchanged.
    """

    path: str
    start_line: int
    end_line: int
    replacement: str
    region_label: str
    original: str = ""

    @model_validator(mode="after")
    def _span_is_orderly(self) -> MutationDescriptor:
        if self.start_line < 1:
            raise ValueError(f"line numbers are 1-based, got start_line={self.start_line}")
        if self.end_line < self.start_line:
            raise ValueError(f"the span ends before it starts: {self.start_line}..{self.end_line}")
        return self

    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1


class DeclineKind(str, Enum):
    """Why the descriptor stage built no edit, as the model must choose it.

    A fixed choice rather than a sentence, so the three cases can be told apart
    without a person reading every reason, and so a model that gave up has to
    name a category rather than hide in a generic sentence.
    """

    ALREADY_PRESENT = "already_present"
    NOT_A_CODE_PROPERTY = "not_a_code_property"
    NOT_ONE_CONTIGUOUS_EDIT = "not_one_contiguous_edit"


#: The outcome each kind of decline is recorded as.
DECLINE_OUTCOMES = {
    DeclineKind.ALREADY_PRESENT: MutationOutcomeKind.ALREADY_PRESENT,
    DeclineKind.NOT_A_CODE_PROPERTY: MutationOutcomeKind.NOT_A_CODE_PROPERTY,
    DeclineKind.NOT_ONE_CONTIGUOUS_EDIT: MutationOutcomeKind.NOT_MUTABLE,
}


class DescriptorDecline(_Model):
    """The descriptor stage's answer when it built no edit, with its reason."""

    kind: DeclineKind
    reason: str


class MutationAttempt(_Model):
    """One defect's trip through the mutation stage, whatever became of it.

    `mutant_text` is the replacement as applied, kept because DR-171 Decision 3
    refuses to spend a second model call confirming that the edit really
    violates the obligation. Recording what was injected is what makes a
    survival arguable by the person reading it, which is weaker than a proof and
    honest about being weaker.

    `killing_tests` names the tests that went red. It is populated only on
    `killed`, and it is the mapping from tests to this defect — not a prediction
    of one.
    """

    defect_id: str
    outcome: MutationOutcomeKind
    descriptor: MutationDescriptor | None = None
    killing_tests: list[str] = Field(default_factory=list)
    tests_run: list[str] = Field(default_factory=list)
    reason: str = ""

    @property
    def settled(self) -> bool:
        return self.outcome in SETTLING_KINDS

    @property
    def tier(self) -> EvidenceTier:
        return tier_for(self.outcome)

    @model_validator(mode="after")
    def _reason_accompanies_every_unsettled_attempt(self) -> MutationAttempt:
        has_reason = bool(self.reason.strip())
        if not self.settled and not has_reason:
            raise ValueError(
                f"outcome {self.outcome.value} for defect {self.defect_id!r} must carry a "
                "reason: a defect the stage tried and could not settle has to stay "
                "distinguishable from one it never tried"
            )
        return self

    @model_validator(mode="after")
    def _killing_tests_only_when_killed(self) -> MutationAttempt:
        if self.killing_tests and self.outcome is not MutationOutcomeKind.KILLED:
            raise ValueError(
                f"outcome {self.outcome.value} for defect {self.defect_id!r} names killing "
                "tests; only a kill has them"
            )
        if self.outcome is MutationOutcomeKind.KILLED and not self.killing_tests:
            raise ValueError(
                f"defect {self.defect_id!r} is recorded as killed but names no test that "
                "went red, so nothing supports the kill"
            )
        return self

    @model_validator(mode="after")
    def _a_settled_attempt_injected_something(self) -> MutationAttempt:
        if self.settled and self.descriptor is None:
            raise ValueError(
                f"defect {self.defect_id!r} is recorded as {self.outcome.value} with no "
                "descriptor, so there is no record of what was injected"
            )
        return self

    @model_validator(mode="after")
    def _killing_tests_were_run(self) -> MutationAttempt:
        unrun = [test for test in self.killing_tests if test not in self.tests_run]
        if unrun:
            raise ValueError(
                f"defect {self.defect_id!r} names killing tests that were not run: "
                f"{', '.join(sorted(unrun))}"
            )
        return self
