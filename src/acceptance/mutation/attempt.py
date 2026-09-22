"""What one injection attempt produced.

DR-171 Decision 8, as revised 2026-09-14. Every defect the mutation stage was
asked about ends with exactly one outcome, and the two outcomes that settle
nothing carry a reason — for the same reason `DefectSet` requires one on an
empty set and `TestOutcome` requires one on a test that did not complete:
"looked and could not" and "did not look" are different, and only one of them is
a defect in the tool.

`killed` and `survived` are the two outcomes where the tests were run against
the edit and read. They are **observed**, but not yet **settled**: an observation
is only evidence about the named defect if the edit really made that defect true.
Measured on #45's own review, about half the edits did not — they repaired a
defect the code already had, changed something else, or broke far more — so an
observed outcome settles the defect and reaches `DEFECT_KILLED` only when its
edit has been verified. An unverified observation is kept and reported, stays at
`STATIC`, and its defect goes to the static judge like any other. A bad edit then
costs compute rather than a wrong tier.

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
    "AlreadyDefective",
    "DeclineKind",
    "DescriptorAnswer",
    "DescriptorDecline",
    "MutationAttempt",
    "MutationDescriptor",
    "MutationOutcomeKind",
    "RepairCorroboration",
    "VerificationStep",
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


#: The kinds where the tests were run against the edit and read. Necessary for an
#: attempt to settle its defect, not sufficient: see `MutationAttempt.settled`.
SETTLING_KINDS = frozenset({MutationOutcomeKind.KILLED, MutationOutcomeKind.SURVIVED})


def tier_for(kind: MutationOutcomeKind, verified: bool = False) -> EvidenceTier:
    """The evidence tier an outcome of `kind` reaches.

    `DEFECT_KILLED` needs both an observed outcome and a verified edit. Anything
    less is `STATIC`, whatever the run observed.

    Routed through `authorize_tier` rather than returned directly, so the
    ceiling this component is allowed to produce is enforced by the one place
    that owns it (CLAUDE.md's evidence-tier invariant) instead of being restated
    here where it could drift.
    """
    reached = kind in SETTLING_KINDS and verified
    tier = EvidenceTier.DEFECT_KILLED if reached else EvidenceTier.STATIC
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
    # The model could not see enough of the code to say which of the defect's
    # two behaviours it has, and was told to say so rather than guess.
    CANNOT_TELL = "cannot_tell"


#: The outcome each kind of decline is recorded as.
DECLINE_OUTCOMES = {
    DeclineKind.ALREADY_PRESENT: MutationOutcomeKind.ALREADY_PRESENT,
    DeclineKind.NOT_A_CODE_PROPERTY: MutationOutcomeKind.NOT_A_CODE_PROPERTY,
    DeclineKind.NOT_ONE_CONTIGUOUS_EDIT: MutationOutcomeKind.NOT_MUTABLE,
    DeclineKind.CANNOT_TELL: MutationOutcomeKind.NOT_MUTABLE,
}


class DescriptorDecline(_Model):
    """The descriptor stage's answer when it built no edit, with its reason."""

    kind: DeclineKind
    reason: str


class AlreadyDefective(_Model):
    """The model's claim that the code already does the defective behaviour.

    Not a skip: it is a claim that the delivered code fails the criterion, and it
    is recorded as a finding. `repair` is the smallest edit the model gave that
    would make the code do the EXPECTED behaviour instead, when it gave one. The
    runner runs the candidate tests against it to corroborate the claim.
    """

    reason: str
    repair: MutationDescriptor | None = None


#: Everything the edit-building step can answer about one defect: an edit that
#: injects it, a claim the code already has it, a typed decline, or nothing usable.
DescriptorAnswer = MutationDescriptor | DescriptorDecline | AlreadyDefective | None


class RepairCorroboration(str, Enum):
    """What running the candidate tests against the repair edit showed.

    The claim itself is a model's reading of the code, at the static tier, and
    none of these raises its tier. They say how far a test run supports it.
    """

    # Every candidate test passed on the repaired code as well as on the code as
    # delivered, so no test pins the expected behaviour. Consistent with the
    # claim: the tests cannot tell the two behaviours apart.
    NO_TEST_PINS_EXPECTED = "no_test_pins_expected"
    # A test that passes on the delivered code failed on the repaired code, so
    # that test asserts the DEFECTIVE behaviour. The stronger finding: the tests
    # lock the defect in.
    A_TEST_ASSERTS_DEFECTIVE = "a_test_asserts_defective"
    # No repair edit was given, or it failed a mechanical check, or its run was
    # not fully observed. The claim stands on the model's reading alone.
    NOT_RUN = "not_run"


class VerificationStep(str, Enum):
    """Which of verification's two questions refused an edit.

    Kept apart so refusals can be counted per question: an edit that changes
    nothing and an edit that changes the wrong thing are different failures of
    the edit-building step, and one number for both hides which is which.
    """

    # The edit does not change the code's behaviour at all.
    BEHAVIOUR_CHANGE = "behaviour_change"
    # The edit changes behaviour, but not from the defect's expected behaviour
    # to its defective one.
    DEFECT_MATCH = "defect_match"


class MutationAttempt(_Model):
    """One defect's trip through the mutation stage, whatever became of it.

    The descriptor is kept whatever became of the edit, so a reader who
    disagrees with what was injected can see exactly what it was.

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
    # Whether the edit was checked and found to make the named defect true.
    # False until something verifies it, and false for every attempt recorded
    # before verification existed — so an old stored review reads back at the
    # static tier rather than claiming evidence nobody checked.
    verified: bool = False
    # Why the edit was or was not accepted as making the defect true. Empty
    # while no verification has run.
    verification_reason: str = ""
    # Which question refused the edit. Empty while no verification has run, and
    # for a verified edit.
    refused_by: VerificationStep | None = None
    # For `already_present` only: the edit that would make the code do the
    # EXPECTED behaviour, what the tests did on it, and which tests failed.
    repair: MutationDescriptor | None = None
    repair_corroboration: RepairCorroboration | None = None
    repair_failing_tests: list[str] = Field(default_factory=list)

    @property
    def observed(self) -> bool:
        """The tests were run against the edit and their results read."""
        return self.outcome in SETTLING_KINDS

    @property
    def settled(self) -> bool:
        """Observed, AND the edit was verified to make the named defect true.

        Only a settled attempt produces verdicts, reaches `DEFECT_KILLED`, and
        removes its defect from the static judge's input.
        """
        return self.observed and self.verified

    @property
    def tier(self) -> EvidenceTier:
        return tier_for(self.outcome, self.verified)

    @model_validator(mode="after")
    def _repair_fields_only_on_already_present(self) -> MutationAttempt:
        has_repair = (
            self.repair is not None
            or self.repair_corroboration is not None
            or bool(self.repair_failing_tests)
        )
        if has_repair and self.outcome is not MutationOutcomeKind.ALREADY_PRESENT:
            raise ValueError(
                f"defect {self.defect_id!r} is {self.outcome.value} and carries a repair; "
                "only an already-present defect has one"
            )
        if self.repair_failing_tests and (
            self.repair_corroboration is not RepairCorroboration.A_TEST_ASSERTS_DEFECTIVE
        ):
            raise ValueError(
                f"defect {self.defect_id!r} names tests that failed on its repair, but "
                "its corroboration does not say a test asserts the defective behaviour"
            )
        return self

    @model_validator(mode="after")
    def _only_an_observed_attempt_is_verified(self) -> MutationAttempt:
        if self.verified and not self.observed:
            raise ValueError(
                f"defect {self.defect_id!r} is {self.outcome.value} and marked verified; "
                "only an edit whose tests were run can be verified"
            )
        if self.verified and self.refused_by is not None:
            raise ValueError(
                f"defect {self.defect_id!r} is marked verified and refused by "
                f"{self.refused_by.value}; an edit is one or the other"
            )
        return self

    @model_validator(mode="after")
    def _reason_accompanies_every_unsettled_attempt(self) -> MutationAttempt:
        has_reason = bool(self.reason.strip())
        if not self.observed and not has_reason:
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
        if self.observed and self.descriptor is None:
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
