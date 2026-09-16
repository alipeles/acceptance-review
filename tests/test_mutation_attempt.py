"""Every attempt carries a typed outcome, and the ones that settle nothing say why.

DR-171 Decision 8 as revised. The validators here exist because a defect nothing
can see is indistinguishable from one that survived, and only one of those is a
defect in the tool.
"""

from __future__ import annotations

import pytest

from acceptance.evidence_tier import EvidenceTier
from acceptance.mutation.attempt import (
    MutationAttempt,
    MutationDescriptor,
    MutationOutcomeKind,
    tier_for,
)


def _descriptor() -> MutationDescriptor:
    return MutationDescriptor(
        path="src.py",
        start_line=2,
        end_line=2,
        replacement="    return 0\n",
        region_label="src.py#0",
    )


class TestTiers:
    def test_both_observed_outcomes_reach_defect_killed_once_verified(self):
        """A survival is as strong as a kill. They disagree about the tests,
        not about how well the answer is known."""
        assert tier_for(MutationOutcomeKind.KILLED, verified=True) is EvidenceTier.DEFECT_KILLED
        assert tier_for(MutationOutcomeKind.SURVIVED, verified=True) is EvidenceTier.DEFECT_KILLED

    def test_an_observed_outcome_stays_static_until_verified(self):
        assert tier_for(MutationOutcomeKind.KILLED) is EvidenceTier.STATIC
        assert tier_for(MutationOutcomeKind.SURVIVED) is EvidenceTier.STATIC

    def test_the_unsettled_outcomes_stay_static(self):
        assert tier_for(MutationOutcomeKind.NOT_MUTABLE) is EvidenceTier.STATIC
        assert tier_for(MutationOutcomeKind.NOT_ATTEMPTED) is EvidenceTier.STATIC

    def test_the_attempt_reports_its_own_tier(self):
        attempt = MutationAttempt(
            defect_id="d1",
            outcome=MutationOutcomeKind.SURVIVED,
            descriptor=_descriptor(),
            tests_run=["t.py::a"],
            verified=True,
        )
        assert attempt.tier is EvidenceTier.DEFECT_KILLED
        assert attempt.settled is True

    def test_an_unverified_attempt_is_observed_but_not_settled(self):
        attempt = MutationAttempt(
            defect_id="d1",
            outcome=MutationOutcomeKind.SURVIVED,
            descriptor=_descriptor(),
            tests_run=["t.py::a"],
        )
        assert attempt.observed is True
        assert attempt.settled is False
        assert attempt.tier is EvidenceTier.STATIC

    def test_an_attempt_whose_tests_never_ran_cannot_be_verified(self):
        with pytest.raises(ValueError, match="only an edit whose tests were run"):
            MutationAttempt(
                defect_id="d1",
                outcome=MutationOutcomeKind.NOT_MUTABLE,
                reason="no region",
                verified=True,
            )

    def test_a_record_stored_before_verification_existed_reads_back_static(self):
        stored = {
            "defect_id": "d1",
            "outcome": "killed",
            "descriptor": _descriptor().model_dump(),
            "tests_run": ["t.py::a"],
            "killing_tests": ["t.py::a"],
        }
        assert MutationAttempt.model_validate(stored).tier is EvidenceTier.STATIC


class TestReasons:
    @pytest.mark.parametrize(
        "outcome", [MutationOutcomeKind.NOT_MUTABLE, MutationOutcomeKind.NOT_ATTEMPTED]
    )
    def test_an_unsettled_outcome_without_a_reason_is_refused(self, outcome):
        with pytest.raises(ValueError, match="must carry a reason"):
            MutationAttempt(defect_id="d1", outcome=outcome)

    @pytest.mark.parametrize(
        "outcome", [MutationOutcomeKind.NOT_MUTABLE, MutationOutcomeKind.NOT_ATTEMPTED]
    )
    def test_an_unsettled_outcome_with_a_reason_is_accepted(self, outcome):
        attempt = MutationAttempt(defect_id="d1", outcome=outcome, reason="no region named")
        assert attempt.settled is False
        assert attempt.tier is EvidenceTier.STATIC

    def test_whitespace_is_not_a_reason(self):
        with pytest.raises(ValueError, match="must carry a reason"):
            MutationAttempt(defect_id="d1", outcome=MutationOutcomeKind.NOT_MUTABLE, reason="   ")


class TestKillingTests:
    def test_a_kill_names_the_tests_that_went_red(self):
        attempt = MutationAttempt(
            defect_id="d1",
            outcome=MutationOutcomeKind.KILLED,
            descriptor=_descriptor(),
            tests_run=["t.py::a", "t.py::b"],
            killing_tests=["t.py::a"],
        )
        assert attempt.killing_tests == ["t.py::a"]

    def test_a_kill_that_names_no_test_is_refused(self):
        with pytest.raises(ValueError, match="names no test that went red"):
            MutationAttempt(
                defect_id="d1",
                outcome=MutationOutcomeKind.KILLED,
                descriptor=_descriptor(),
                tests_run=["t.py::a"],
            )

    def test_a_survival_that_names_a_killing_test_is_refused(self):
        with pytest.raises(ValueError, match="only a kill has them"):
            MutationAttempt(
                defect_id="d1",
                outcome=MutationOutcomeKind.SURVIVED,
                descriptor=_descriptor(),
                tests_run=["t.py::a"],
                killing_tests=["t.py::a"],
            )

    def test_a_killing_test_that_was_never_run_is_refused(self):
        """Guards the join between the sandbox result and this record. A killing
        test absent from `tests_run` means the two were built from different
        test sets, which would credit a kill to a run that never happened."""
        with pytest.raises(ValueError, match="not run"):
            MutationAttempt(
                defect_id="d1",
                outcome=MutationOutcomeKind.KILLED,
                descriptor=_descriptor(),
                tests_run=["t.py::b"],
                killing_tests=["t.py::a"],
            )


class TestDescriptorIsRecorded:
    @pytest.mark.parametrize("outcome", [MutationOutcomeKind.KILLED, MutationOutcomeKind.SURVIVED])
    def test_a_settled_attempt_without_a_descriptor_is_refused(self, outcome):
        """An observed result with no record of what was injected cannot be
        checked by anyone, including the verification that gates its tier."""
        killing = ["t.py::a"] if outcome is MutationOutcomeKind.KILLED else []
        with pytest.raises(ValueError, match="no record of what was injected"):
            MutationAttempt(
                defect_id="d1",
                outcome=outcome,
                tests_run=["t.py::a"],
                killing_tests=killing,
            )


class TestSpans:
    def test_a_backwards_span_is_refused(self):
        with pytest.raises(ValueError, match="ends before it starts"):
            MutationDescriptor(
                path="src.py", start_line=5, end_line=2, replacement="", region_label="src.py#0"
            )

    def test_a_zero_line_number_is_refused(self):
        with pytest.raises(ValueError, match="1-based"):
            MutationDescriptor(
                path="src.py", start_line=0, end_line=1, replacement="", region_label="src.py#0"
            )

    def test_line_count_is_inclusive(self):
        descriptor = MutationDescriptor(
            path="src.py", start_line=4, end_line=6, replacement="", region_label="src.py#0"
        )
        assert descriptor.line_count == 3
