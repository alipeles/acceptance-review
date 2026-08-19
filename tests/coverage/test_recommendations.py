"""M7.1 acceptance: for a criterion whose test evidence is weak, a §9.5
structured recommendation is produced with every field populated — the
non-discriminating contractual-accrual/daily-rate case (archetype #4).

Generation is a schema-constrained model call; per the replay-first invariant
these tests inject the recorded response via completion_fn — no live calls.
Recommendation *quality* against the real model is shown by the PR's record run."""

import pytest

from acceptance.coverage.recommendations import recommend_tests
from acceptance.evidence.discrimination import ObligationDiscrimination, PlausibleDefect
from acceptance.llm import SchemaValidationError
from acceptance.review_state import (
    ChangeSet,
    DiffHunk,
    FileChange,
    Obligation,
    ObligationType,
    RequiredEvidence,
)
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import client_returning as _client_returning


def _obligation(obligation_id: str, description: str, evidence_class: str | None) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=description,
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior=description,
        evidence_class=evidence_class,
    )


def _change_set() -> ChangeSet:
    return ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="billing.py",
                status="modified",
                category="source",
                hunks=[
                    DiffHunk(
                        header="@@ -1 +3 @@",
                        old_start=1,
                        old_lines=1,
                        new_start=1,
                        new_lines=3,
                        content="+    return round(monthly_price / days_in_month * days_used, 2)",
                    ),
                ],
            ),
        ],
    )


def _exploding_client():
    import tempfile

    from acceptance.llm import Mode, ModelClient, TranscriptStore

    def boom(**kwargs):
        raise AssertionError("a model call was issued with no weak obligations")

    return ModelClient(
        model="x", mode=Mode.RECORD, store=TranscriptStore(tempfile.mkdtemp()), completion_fn=boom
    )


def test_weak_criterion_gets_a_fully_populated_recommendation():
    # Archetype #4's daily-rate gap: the only test uses a 30-day month, where
    # price/days_in_month and a hard-coded price/30 give the same answer.
    obligations = [
        _obligation(
            "daily-rate",
            "Daily rate is monthly_price divided by days_in_month",
            "nominally_supported",
        ),
    ]
    discriminations = [
        ObligationDiscrimination(
            obligation_id="daily-rate",
            defects=[
                PlausibleDefect(
                    description="hard-codes price/30 instead of price/days_in_month",
                    would_be_caught=False,
                    reason="a 30-day month gives the same result either way",
                )
            ],
            discriminating=False,
        )
    ]
    response = {
        "recommendations": [
            {
                "obligation_id": "daily-rate",
                "required_inputs": "A month whose length is not 30, e.g. days_in_month=28.",
                "boundary_conditions": "0 days used and a full month.",
                "expected_output": "prorate(28*price, 14, 28) uses price/28, differing from price/30.",
                "required_assertions": ["assert prorate(280, 14, 28) == 140.0"],
                "plausible_defect": "implementation hard-codes /30 instead of /days_in_month",
                "repo_conventions": "add to test_billing.py alongside test_half_of_a_month",
            }
        ]
    }

    recommendations = recommend_tests(
        obligations, discriminations, _change_set(), _client_returning(response)
    ).recommendations

    assert len(recommendations) == 1
    rec = recommendations[0]
    assert rec.obligation_id == "daily-rate"
    assert rec.criterion == "Daily rate is monthly_price divided by days_in_month"
    # Every §9.5 field is populated.
    assert rec.required_inputs
    assert rec.boundary_conditions
    assert rec.expected_output
    assert rec.required_assertions
    assert "30" in rec.plausible_defect
    assert rec.repo_conventions


def test_strongly_supported_obligations_get_no_recommendation_and_no_model_call():
    obligations = [
        _obligation("solid", "Well-tested behavior", "strongly_supported"),
    ]
    # The exploding client proves no model call is issued when nothing is weak.
    result = recommend_tests(obligations, [], _change_set(), _exploding_client())
    assert result.recommendations == []
    assert result.unobtained == []


def test_unclassified_obligations_are_not_recommended():
    # evidence_class=None means "not yet classified", not "weak" — skip it.
    obligations = [_obligation("pending", "Not yet classified", None)]
    result = recommend_tests(obligations, [], _change_set(), _exploding_client())
    assert result.recommendations == []
    assert result.unobtained == []


def test_recommendation_round_trips_through_persistence():
    obligations = [_obligation("daily-rate", "Daily rate rule", "partially_supported")]
    response = {
        "recommendations": [
            {
                "obligation_id": "daily-rate",
                "required_inputs": "i",
                "boundary_conditions": "b",
                "expected_output": "o",
                "required_assertions": ["a"],
                "plausible_defect": "d",
                "repo_conventions": "c",
            }
        ]
    }
    from acceptance.review_state import TestRecommendation

    rec = recommend_tests(
        obligations, [], _change_set(), _client_returning(response)
    ).recommendations[0]
    assert TestRecommendation.from_dict(rec.to_dict()) == rec


def _two_weak() -> tuple[list[Obligation], list[ObligationDiscrimination]]:
    obligations = [
        _obligation("daily-rate", "Daily rate uses days_in_month", "nominally_supported"),
        _obligation("proration", "Proration handles partial months", "unsupported"),
    ]
    discriminations = [
        ObligationDiscrimination(
            obligation_id=obligation.id,
            defects=[
                PlausibleDefect(
                    description="the behaviour is wrong",
                    would_be_caught=False,
                    reason="no discriminating input",
                )
            ],
            discriminating=False,
        )
        for obligation in obligations
    ]
    return obligations, discriminations


def _recommendation(obligation_id: str) -> dict:
    return {
        "obligation_id": obligation_id,
        "required_inputs": "a month whose length is not 30",
        "boundary_conditions": "0 days and a full month",
        "expected_output": "price/28*days",
        "required_assertions": ["assert prorate(280, 14, 28) == 140.0"],
        "plausible_defect": "hard-codes /30",
        "repo_conventions": "test_billing.py",
    }


def test_a_response_skipping_a_weak_obligation_records_it_as_not_obtained():
    """The "always" half of the invariant, kept — but paid for with one
    obligation instead of the whole review (#275).

    #218 made a skipped obligation visible by raising, which was right about the
    visibility and wrong about the price: on a real run one omission out of
    thirteen discarded twelve honoured prescriptions, the verdict, and every
    finding the earlier stages had produced. The omission is still refused a
    silent pass — it becomes an explicit not-obtained record — and the answers
    that did come back survive.
    """
    obligations, discriminations = _two_weak()
    response = {"recommendations": [_recommendation("daily-rate")]}
    log = UnusableAnswerLog()

    result = recommend_tests(
        obligations, discriminations, _change_set(), _client_returning(response), log
    )

    assert [r.obligation_id for r in result.recommendations] == ["daily-rate"]
    assert [u.obligation_id for u in result.unobtained] == ["proration"]
    # Not merely present: it says which criterion went unanswered and that the
    # answer was never obtained, so a reader cannot mistake it for a complete one.
    unobtained = result.unobtained[0]
    assert unobtained.criterion == "Proration handles partial months"
    assert "no prescription was produced" in unobtained.reason
    assert "1 of 2" in unobtained.reason or "2 criteria and returned 1" in unobtained.reason
    # And the evidence axis is told, which is what keeps the verdict honest.
    assert log.indeterminate_obligations == {"proration"}


def test_an_omission_does_not_mark_the_answered_obligations_indeterminate():
    """The other half of the same guarantee: a positive answer we could honour
    keeps its judgment. Marking the whole call indeterminate would discard
    twelve good prescriptions in a different way."""
    obligations, discriminations = _two_weak()
    response = {"recommendations": [_recommendation("daily-rate")]}
    log = UnusableAnswerLog()

    recommend_tests(obligations, discriminations, _change_set(), _client_returning(response), log)

    assert "daily-rate" not in log.indeterminate_obligations


def test_a_response_naming_a_non_weak_obligation_is_rejected():
    """The "only" half. It was enforced by dropping the entry, which is the same
    silence in the other direction: a recommendation the call never asked for
    means the model answered about something else, and that is worth knowing."""
    obligations, discriminations = _two_weak()
    response = {
        "recommendations": [
            _recommendation("daily-rate"),
            _recommendation("proration"),
            _recommendation("some-other-obligation"),
        ]
    }

    with pytest.raises(SchemaValidationError) as raised:
        recommend_tests(obligations, discriminations, _change_set(), _client_returning(response))

    assert "some-other-obligation" in str(raised.value)


def test_a_duplicate_recommendation_is_rejected():
    obligations, discriminations = _two_weak()
    response = {
        "recommendations": [
            _recommendation("daily-rate"),
            _recommendation("daily-rate"),
            _recommendation("proration"),
        ]
    }

    with pytest.raises(SchemaValidationError) as raised:
        recommend_tests(obligations, discriminations, _change_set(), _client_returning(response))

    assert "more than once" in str(raised.value)


def test_every_weak_obligation_gets_exactly_one_recommendation():
    """The invariant stated positively, and in weak-obligation order rather than
    response order — two recorded runs over one input must be byte-identical."""
    obligations, discriminations = _two_weak()
    response = {
        "recommendations": [
            _recommendation("proration"),
            _recommendation("daily-rate"),
        ]
    }

    result = recommend_tests(
        obligations, discriminations, _change_set(), _client_returning(response)
    )

    assert [r.obligation_id for r in result.recommendations] == ["daily-rate", "proration"]
    assert result.unobtained == []


def test_two_runs_over_one_omitting_response_produce_identical_state():
    """Determinism over the new path: the not-obtained record is derived from
    the supplied set and the response, both of which are fixed, so nothing about
    it may vary between runs (M0.5)."""
    obligations, discriminations = _two_weak()
    response = {"recommendations": [_recommendation("daily-rate")]}

    first = recommend_tests(
        obligations, discriminations, _change_set(), _client_returning(response)
    )
    second = recommend_tests(
        obligations, discriminations, _change_set(), _client_returning(response)
    )

    assert [u.to_dict() for u in first.unobtained] == [u.to_dict() for u in second.unobtained]
    assert [r.to_dict() for r in first.recommendations] == [
        r.to_dict() for r in second.recommendations
    ]


# --- #153: no test is prescribed for a boundary obligation --------------------


def test_no_test_is_recommended_for_a_code_evidence_only_obligation():
    """#153's acceptance, and #146's original complaint. The exclusion
    "Converting the rest of the suite is out of scope" was rated
    partially_supported and earned a test recommendation — but there is no
    behavioural test for "we didn't also do something else", so the prescription
    named evidence that cannot exist.

    The exploding client is the assertion that matters: a boundary obligation
    must not merely be dropped from the output, it must not reach the model at
    all. A recommendation call that ran and returned nothing would pass a
    check on the result alone while still costing a call and a transcript.
    """
    boundary = Obligation(
        id="pagination",
        description="The change does not alter how the invoice list is paginated",
        type=ObligationType.INVARIANT,
        importance="critical",
        explicit=True,
        observable_behavior="pagination code appearing in the diff",
        evidence_class="unsupported",
        required_evidence=RequiredEvidence.CODE_ONLY,
        required_evidence_reason="no test can assert that excluded work was not done",
        satisfied_by_absence=True,
    )

    result = recommend_tests([boundary], [], _change_set(), _exploding_client())

    assert result.recommendations == []
    # And it is not recorded as not-obtained either: nothing was asked about it,
    # so there is no missing answer. #266's decision that no test is owed here
    # is a settled answer, not an absent one.
    assert result.unobtained == []


def test_a_weak_ordinary_obligation_alongside_a_boundary_one_still_recommends():
    """The boundary the test above cannot draw on its own: filtering must remove
    the boundary obligation from the batch without suppressing the real gap
    sitting next to it. Asserting the recommendation names the ordinary
    obligation, not merely that something came back."""
    ordinary = _obligation(
        "daily-rate", "Daily rate is monthly_price divided by days_in_month", "nominally_supported"
    )
    boundary = Obligation(
        id="pagination",
        description="The change does not alter how the invoice list is paginated",
        type=ObligationType.INVARIANT,
        importance="critical",
        explicit=True,
        observable_behavior="pagination code appearing in the diff",
        evidence_class="unsupported",
        required_evidence=RequiredEvidence.CODE_ONLY,
        required_evidence_reason="no test can assert that excluded work was not done",
        satisfied_by_absence=True,
    )
    client = _client_returning(
        {
            "recommendations": [
                {
                    "obligation_id": "daily-rate",
                    "required_inputs": "A month whose length is not 30, e.g. days_in_month=28.",
                    "boundary_conditions": "0 days used and a full month.",
                    "expected_output": "price/28 differs from price/30.",
                    "required_assertions": ["assert prorate(280, 14, 28) == 140.0"],
                    "plausible_defect": "hard-codes /30 instead of /days_in_month",
                    "repo_conventions": "test_billing.py",
                }
            ]
        }
    )

    result = recommend_tests([ordinary, boundary], [], _change_set(), client)

    assert [r.obligation_id for r in result.recommendations] == ["daily-rate"]
    assert result.unobtained == []
