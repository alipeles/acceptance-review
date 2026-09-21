"""The injection run decides which defect-and-test pairs are worth a model call.

#340. The static pair judgement is the cost of a review — 1,330 of 1,394 calls
and $10.09 of $11.59 on #45's Gate 2 run 3 — and the answer is "no" about 99% of
the time. The injection run already ran every candidate test against every edit
it could build, which answers the same question for free.

**The whole risk of this feature is that the run is wrong about half the time.**
An edit nobody verified may not have made the named defect true, so a test
passing under it is a reason to spend the call elsewhere and nothing more. Every
assertion here is about keeping that distinction: a dropped pair is unjudged, it
raises `unknown`, it derives no verdict, and where the run turned out to have
shown nothing usable the pairs are asked after all.
"""

from __future__ import annotations

from acceptance.defects.support import derive_support
from acceptance.evidence_tier import EvidenceTier
from acceptance.mutation.attempt import MutationAttempt, MutationDescriptor, MutationOutcomeKind
from acceptance.mutation.verdicts import pairs_not_worth_asking
from acceptance.review_state import (
    Defect,
    DefectSet,
    DefectType,
    Obligation,
    ObligationType,
    PairVerdict,
    UnjudgedCause,
    UnjudgedPair,
)


def _descriptor() -> MutationDescriptor:
    return MutationDescriptor(
        path="a.py", start_line=1, end_line=1, replacement="x\n", region_label="a.py#0"
    )


def _killed(defect_id: str, killing: list[str], ran: list[str], verified: bool = False):
    return MutationAttempt(
        defect_id=defect_id,
        outcome=MutationOutcomeKind.KILLED,
        descriptor=_descriptor(),
        tests_run=ran,
        killing_tests=killing,
        verified=verified,
    )


def _survived(defect_id: str, ran: list[str], verified: bool = False) -> MutationAttempt:
    return MutationAttempt(
        defect_id=defect_id,
        outcome=MutationOutcomeKind.SURVIVED,
        descriptor=_descriptor(),
        tests_run=ran,
        verified=verified,
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


def _obligation(obligation_id: str = "o1") -> Obligation:
    return Obligation(
        id=obligation_id,
        type=ObligationType.FUNCTIONAL,
        description="the criterion",
        importance="normal",
        explicit=True,
        observable_behavior="b",
    )


class TestWhichPairsTheRunAnswers:
    def test_a_test_that_kept_passing_under_the_edit_is_not_asked(self):
        skipped = pairs_not_worth_asking([_killed("d1", ["t::a"], ["t::a", "t::b", "t::c"])])
        assert set(skipped) == {("d1", "t::b"), ("d1", "t::c")}

    def test_a_test_that_failed_under_the_edit_is_still_asked(self):
        """A test going red does not on its own say the named defect is what it
        caught, so the model is still asked about it."""
        skipped = pairs_not_worth_asking([_killed("d1", ["t::a"], ["t::a", "t::b"])])
        assert ("d1", "t::a") not in skipped

    def test_a_survival_skips_nothing(self):
        """The #340 rule that keeps this honest. An edit nothing failed under
        cannot be told apart from an edit that changed nothing, so it has
        demonstrated nothing and may remove no question."""
        assert pairs_not_worth_asking([_survived("d1", ["t::a", "t::b", "t::c"])]) == {}

    def test_a_settled_attempt_skips_nothing(self):
        """Its defect leaves through `remaining_defect_sets` and every one of its
        pairs gets a real verdict from `verdicts_from`. Listing them here too
        would record the same pair as both judged and skipped."""
        attempt = _killed("d1", ["t::a"], ["t::a", "t::b"], verified=True)
        assert pairs_not_worth_asking([attempt]) == {}

    def test_the_reason_says_the_edit_was_not_verified(self):
        """The sentence a reader sees. It has to refuse the inference the numbers
        invite — that the test was shown not to catch the defect."""
        skipped = pairs_not_worth_asking([_killed("d1", ["t::a"], ["t::a", "t::b"])])
        reason = skipped[("d1", "t::b")]
        assert "not verified" in reason
        assert "not evidence that the test fails to catch the defect" in reason


class TestADroppedPairIsNotASurvival:
    """The rating must not firm up because an unverified edit removed a question.

    `UnjudgedCause.PREFILTERED` is excluded from the `unknown` tally because the
    prefilter PROVES its exclusions. Nothing proves this one, so it is counted.
    """

    def test_it_raises_unknown_rather_than_reading_as_uncovered(self):
        dropped = UnjudgedPair(
            defect_id="d1",
            test_id="t::b",
            cause=UnjudgedCause.PASSED_UNDER_EDIT,
            reason="not asked",
        )
        (result,) = derive_support([_obligation()], _sets("d1"), [], [dropped])
        assert result.unknown == 1
        assert result.covered == 0
        assert result.evidence_class == "indeterminate"

    def test_a_prefiltered_pair_still_does_not(self):
        """The control. Without it this asserts only that `derive_support` counts
        something, not that it tells the two causes apart."""
        proved = UnjudgedPair(
            defect_id="d1",
            test_id="t::b",
            cause=UnjudgedCause.PREFILTERED,
            reason="no path from the test to the defect",
        )
        (result,) = derive_support([_obligation()], _sets("d1"), [], [proved])
        assert result.unknown == 0
        assert result.evidence_class == "unsupported"

    def test_it_contributes_no_verdict_and_no_test_link(self):
        dropped = UnjudgedPair(
            defect_id="d1",
            test_id="t::b",
            cause=UnjudgedCause.PASSED_UNDER_EDIT,
            reason="not asked",
        )
        (result,) = derive_support([_obligation()], _sets("d1"), [], [dropped])
        assert result.test_links == []
        assert result.achieved_tier is EvidenceTier.STATIC

    def test_it_cannot_make_a_criterion_strongly_supported(self):
        """The failure this feature could cause and must not: a criterion rated
        on two defects, one killed and one whose only pairs were dropped. If a
        dropped pair read as an established survival the second defect would be
        merely uncovered, and a later kill on it would round the criterion up."""
        killed = PairVerdict(defect_id="d1", test_id="t::a", kills=True, reason="it fails")
        dropped = UnjudgedPair(
            defect_id="d2",
            test_id="t::b",
            cause=UnjudgedCause.PASSED_UNDER_EDIT,
            reason="not asked",
        )
        (result,) = derive_support([_obligation()], _sets("d1", "d2"), [killed], [dropped])
        assert result.evidence_class != "strongly_supported"
        assert result.unknown == 1
