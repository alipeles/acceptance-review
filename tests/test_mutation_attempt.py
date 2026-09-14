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
    def test_both_settling_outcomes_reach_defect_killed(self):
        """A survival is as strong as a kill. They disagree about the tests,
        not about how well the answer is known."""
        assert tier_for(MutationOutcomeKind.KILLED) is EvidenceTier.DEFECT_KILLED
        assert tier_for(MutationOutcomeKind.SURVIVED) is EvidenceTier.DEFECT_KILLED

    def test_the_unsettled_outcomes_stay_static(self):
        assert tier_for(MutationOutcomeKind.NOT_MUTABLE) is EvidenceTier.STATIC
        assert tier_for(MutationOutcomeKind.NOT_ATTEMPTED) is EvidenceTier.STATIC

    def test_the_attempt_reports_its_own_tier(self):
        attempt = MutationAttempt(
            defect_id="d1",
            outcome=MutationOutcomeKind.SURVIVED,
            descriptor=_descriptor(),
            tests_run=["t.py::a"],
        )
        assert attempt.tier is EvidenceTier.DEFECT_KILLED
        assert attempt.settled is True


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
        """DR-171 Decision 3 spends no model call confirming the mutant really
        violates the obligation. Recording what was injected is the whole of
        what replaces that, so a settled attempt without it is unarguable."""
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
