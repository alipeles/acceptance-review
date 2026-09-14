"""Executed verdicts join the record the rating already reads, and the static
judge is left only what execution could not settle.

DR-171 Decision 7. The two halves are tested together because they are two
readings of one fact: a settled defect produces verdicts *and* disappears from
the question put to the model. If those ever disagreed, a defect would be both
paid for and answered, or neither.
"""

from __future__ import annotations

from acceptance.defects.support import derive_support
from acceptance.evidence_tier import EvidenceTier
from acceptance.mutation.attempt import MutationAttempt, MutationDescriptor, MutationOutcomeKind
from acceptance.mutation.verdicts import remaining_defect_sets, verdicts_from
from acceptance.review_state import (
    Defect,
    DefectSet,
    DefectType,
    Obligation,
    ObligationType,
    PairVerdict,
)


def _defect(defect_id: str) -> Defect:
    return Defect(
        id=defect_id,
        obligation_id="o1",
        type=DefectType.OTHER,
        description=f"description of {defect_id}",
    )


def _sets(*defect_ids: str, obligation_id: str = "o1") -> list[DefectSet]:
    return [
        DefectSet(
            obligation_id=obligation_id,
            defects=[
                Defect(
                    id=defect_id,
                    obligation_id=obligation_id,
                    type=DefectType.OTHER,
                    description=f"description of {defect_id}",
                )
                for defect_id in defect_ids
            ],
        )
    ]


def _descriptor() -> MutationDescriptor:
    return MutationDescriptor(
        path="a.py", start_line=1, end_line=1, replacement="x\n", region_label="a.py#0"
    )


def _killed(defect_id: str, killing: list[str], ran: list[str]) -> MutationAttempt:
    return MutationAttempt(
        defect_id=defect_id,
        outcome=MutationOutcomeKind.KILLED,
        descriptor=_descriptor(),
        tests_run=ran,
        killing_tests=killing,
    )


def _survived(defect_id: str, ran: list[str]) -> MutationAttempt:
    return MutationAttempt(
        defect_id=defect_id,
        outcome=MutationOutcomeKind.SURVIVED,
        descriptor=_descriptor(),
        tests_run=ran,
    )


def _not_mutable(defect_id: str) -> MutationAttempt:
    return MutationAttempt(
        defect_id=defect_id,
        outcome=MutationOutcomeKind.NOT_MUTABLE,
        reason="no span to replace",
    )


class TestVerdictsFrom:
    def test_a_kill_records_the_red_test_as_killing(self):
        verdicts = verdicts_from([_killed("d1", ["t::a"], ["t::a", "t::b"])], _sets("d1"))
        killing = [v for v in verdicts if v.kills]
        assert [v.test_id for v in killing] == ["t::a"]

    def test_every_test_the_mutant_ran_against_gets_a_verdict(self):
        """A pair nobody recorded is indistinguishable from one judged
        *survives*, which is why the static side has `UnjudgedPair`."""
        verdicts = verdicts_from([_killed("d1", ["t::a"], ["t::a", "t::b"])], _sets("d1"))
        assert sorted(v.test_id for v in verdicts) == ["t::a", "t::b"]

    def test_a_survival_records_every_test_as_not_killing(self):
        verdicts = verdicts_from([_survived("d1", ["t::a", "t::b"])], _sets("d1"))
        assert all(v.kills is False for v in verdicts)
        assert len(verdicts) == 2

    def test_executed_verdicts_carry_the_defect_killed_tier(self):
        verdicts = verdicts_from([_survived("d1", ["t::a"])], _sets("d1"))
        assert all(v.tier is EvidenceTier.DEFECT_KILLED for v in verdicts)

    def test_an_unsettled_attempt_produces_no_verdict(self):
        assert verdicts_from([_not_mutable("d1")], _sets("d1")) == []

    def test_the_defect_text_is_carried_so_a_later_run_can_identify_it(self):
        verdicts = verdicts_from([_survived("d1", ["t::a"])], _sets("d1"))
        assert "description of d1" in verdicts[0].defect_text

    def test_no_carry_key_so_an_executed_verdict_is_never_carried_forward(self):
        """Re-running costs CPU time and zero tokens, which is cheaper than
        asserting that an old run still describes the code."""
        verdicts = verdicts_from([_survived("d1", ["t::a"])], _sets("d1"))
        assert verdicts[0].carry_key == ""

    def test_the_reason_says_the_answer_was_observed(self):
        verdicts = verdicts_from([_survived("d1", ["t::a"])], _sets("d1"))
        assert "injected" in verdicts[0].reason


class TestRemainingDefectSets:
    def test_a_settled_defect_is_removed_from_the_static_question(self):
        remaining = remaining_defect_sets([_survived("d1", ["t::a"])], _sets("d1", "d2"))
        assert [d.id for d in remaining[0].defects] == ["d2"]

    def test_a_set_whose_defects_were_all_settled_is_dropped_entirely(self):
        """Passing it on empty would need a reason, and one written here would
        claim the enumeration found nothing plausible when execution in fact
        answered all of it."""
        assert remaining_defect_sets([_survived("d1", ["t::a"])], _sets("d1")) == []

    def test_an_unsettled_defect_stays(self):
        remaining = remaining_defect_sets([_not_mutable("d1")], _sets("d1"))
        assert [d.id for d in remaining[0].defects] == ["d1"]

    def test_nothing_settled_leaves_the_sets_untouched(self):
        sets = _sets("d1", "d2")
        assert remaining_defect_sets([_not_mutable("d1")], sets) == sets

    def test_a_set_for_another_criterion_is_untouched(self):
        sets = _sets("d1") + _sets("d9", obligation_id="o2")
        remaining = remaining_defect_sets([_survived("d1", ["t::a"])], sets)
        assert [s.obligation_id for s in remaining] == ["o2"]


class TestTheRatingReadsBoth:
    """The point of one record type: `derive_support` does not know or care
    which stage produced a verdict."""

    def _obligation(self) -> Obligation:
        return Obligation(
            id="o1",
            description="d",
            type=ObligationType.FUNCTIONAL,
            importance="normal",
            explicit=True,
            observable_behavior="b",
        )

    def test_an_executed_kill_counts_toward_coverage(self):
        results = derive_support(
            [self._obligation()],
            _sets("d1"),
            verdicts_from([_killed("d1", ["t::a"], ["t::a"])], _sets("d1")),
            [],
        )
        assert results[0].covered == 1
        assert results[0].evidence_class == "strongly_supported"

    def test_a_fully_executed_criterion_reaches_the_defect_killed_tier(self):
        results = derive_support(
            [self._obligation()],
            _sets("d1"),
            verdicts_from([_killed("d1", ["t::a"], ["t::a"])], _sets("d1")),
            [],
        )
        assert results[0].achieved_tier is EvidenceTier.DEFECT_KILLED

    def test_one_predicted_defect_holds_the_criterion_at_static(self):
        """The weakest input decides. A criterion cannot be better known than
        the defect whose answer was guessed."""
        executed = verdicts_from([_killed("d1", ["t::a"], ["t::a"])], _sets("d1", "d2"))
        predicted = [PairVerdict(defect_id="d2", test_id="t::a", kills=True)]
        results = derive_support([self._obligation()], _sets("d1", "d2"), executed + predicted, [])
        assert results[0].evidence_class == "strongly_supported"
        assert results[0].achieved_tier is EvidenceTier.STATIC

    def test_a_defect_with_no_verdict_at_all_holds_it_at_static(self):
        """Otherwise a criterion whose only answered defect was executed would
        claim `DEFECT_KILLED` while the rest was never looked at."""
        results = derive_support(
            [self._obligation()],
            _sets("d1", "d2"),
            verdicts_from([_killed("d1", ["t::a"], ["t::a"])], _sets("d1", "d2")),
            [],
        )
        assert results[0].achieved_tier is EvidenceTier.STATIC

    def test_a_review_with_no_execution_is_unchanged(self):
        """§8.3's graceful degradation, structural rather than promised: a
        repository whose tests cannot run is the case where every verdict stays
        `STATIC`, with no separate mode."""
        results = derive_support(
            [self._obligation()],
            _sets("d1"),
            [PairVerdict(defect_id="d1", test_id="t::a", kills=True)],
            [],
        )
        assert results[0].evidence_class == "strongly_supported"
        assert results[0].achieved_tier is EvidenceTier.STATIC
