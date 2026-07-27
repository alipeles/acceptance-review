"""M7.1 acceptance: for a criterion whose test evidence is weak, a §9.5
structured recommendation is produced with every field populated — the
non-discriminating contractual-accrual/daily-rate case (archetype #4).

Generation is a schema-constrained model call; per the replay-first invariant
these tests inject the recorded response via completion_fn — no live calls.
Recommendation *quality* against the real model is shown by the PR's record run."""

from acceptance.coverage.recommendations import recommend_tests
from acceptance.evidence.discrimination import ObligationDiscrimination, PlausibleDefect
from acceptance.review_state import ChangeSet, DiffHunk, FileChange, Obligation, ObligationType
from tests.support import client_returning as _client_returning


def _obligation(obligation_id: str, description: str, evidence_class: str | None) -> Obligation:
    return Obligation(
        id=obligation_id, description=description, type=ObligationType.FUNCTIONAL,
        importance="critical", explicit=True, observable_behavior=description,
        evidence_class=evidence_class,
    )


def _change_set() -> ChangeSet:
    return ChangeSet(base_revision="a", head_revision="b", files=[
        FileChange(path="billing.py", status="modified", category="source", hunks=[
            DiffHunk(header="@@ -1 +3 @@", old_start=1, old_lines=1, new_start=1, new_lines=3,
                     content="+    return round(monthly_price / days_in_month * days_used, 2)"),
        ]),
    ])


def _exploding_client():
    from acceptance.llm import Mode, ModelClient, TranscriptStore
    import tempfile

    def boom(**kwargs):
        raise AssertionError("a model call was issued with no weak obligations")

    return ModelClient(
        model="x", mode=Mode.RECORD, store=TranscriptStore(tempfile.mkdtemp()), completion_fn=boom
    )


def test_weak_criterion_gets_a_fully_populated_recommendation():
    # Archetype #4's daily-rate gap: the only test uses a 30-day month, where
    # price/days_in_month and a hard-coded price/30 give the same answer.
    obligations = [
        _obligation("daily-rate", "Daily rate is monthly_price divided by days_in_month",
                    "nominally_supported"),
    ]
    discriminations = [
        ObligationDiscrimination(
            obligation_id="daily-rate",
            defects=[PlausibleDefect(
                description="hard-codes price/30 instead of price/days_in_month",
                would_be_caught=False, reason="a 30-day month gives the same result either way",
            )],
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
    )

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
    recommendations = recommend_tests(obligations, [], _change_set(), _exploding_client())
    assert recommendations == []


def test_unclassified_obligations_are_not_recommended():
    # evidence_class=None means "not yet classified", not "weak" — skip it.
    obligations = [_obligation("pending", "Not yet classified", None)]
    recommendations = recommend_tests(obligations, [], _change_set(), _exploding_client())
    assert recommendations == []


def test_recommendation_round_trips_through_persistence():
    obligations = [_obligation("daily-rate", "Daily rate rule", "partially_supported")]
    response = {
        "recommendations": [
            {
                "obligation_id": "daily-rate", "required_inputs": "i", "boundary_conditions": "b",
                "expected_output": "o", "required_assertions": ["a"], "plausible_defect": "d",
                "repo_conventions": "c",
            }
        ]
    }
    from acceptance.review_state import TestRecommendation

    rec = recommend_tests(obligations, [], _change_set(), _client_returning(response))[0]
    assert TestRecommendation.from_dict(rec.to_dict()) == rec
