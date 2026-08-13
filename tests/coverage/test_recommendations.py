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
    AdmissibleEvidence,
    ChangeSet,
    DiffHunk,
    FileChange,
    Obligation,
    ObligationType,
)
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
    outcome = recommend_tests(obligations, [], _change_set(), _exploding_client())
    assert outcome.recommendations == []
    assert outcome.unevidenceable == []


def test_unclassified_obligations_are_not_recommended():
    # evidence_class=None means "not yet classified", not "weak" — skip it.
    obligations = [_obligation("pending", "Not yet classified", None)]
    outcome = recommend_tests(obligations, [], _change_set(), _exploding_client())
    assert outcome.recommendations == []
    assert outcome.unevidenceable == []


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


def test_a_response_skipping_a_weak_obligation_is_rejected():
    """The "always" half of the invariant, and the defect #218 removes.

    This stage used to iterate the response and keep what it could place, so a
    response answering one of two weak obligations produced a report where the
    other silently carried no recommendation — indistinguishable from a complete
    answer. That is M1.2.r1's missing disposition, one stage downstream.
    """
    obligations, discriminations = _two_weak()
    response = {"recommendations": [_recommendation("daily-rate")]}

    with pytest.raises(SchemaValidationError) as raised:
        recommend_tests(obligations, discriminations, _change_set(), _client_returning(response))

    message = str(raised.value)
    assert "proration" in message
    assert "1 of 2" in message


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

    recommendations = recommend_tests(
        obligations, discriminations, _change_set(), _client_returning(response)
    ).recommendations

    assert [r.obligation_id for r in recommendations] == ["daily-rate", "proration"]


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
        admissible_evidence=AdmissibleEvidence.CODE_ONLY,
    )

    result = recommend_tests([boundary], [], _change_set(), _exploding_client())

    assert result.recommendations == []
    # #266 gave the stage a way to say "no test can evidence this", which is the
    # same judgement #153 makes here — but by a different route, and this one
    # must stay the silent route. A boundary obligation never reaches the call,
    # so it earns no refusal record either; one would imply the model was asked.
    assert result.unevidenceable == []


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
        admissible_evidence=AdmissibleEvidence.CODE_ONLY,
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


# --- #266: a criterion no test can evidence ----------------------------------


def _refusal(obligation_id: str, reason: str = "a property of a CI step, not of any test"):
    return {"obligation_id": obligation_id, "reason": reason}


def test_a_declined_obligation_does_not_abort_the_review():
    """#266's headline. Before this, the only way to answer a criterion no test
    could evidence was to say nothing about it — which the completeness guard
    correctly rejects, taking every other answer in the call down with it."""
    obligations = [
        _obligation("checkout-action", "The checkout action is not on Node 20", "unsupported"),
    ]
    response = {"recommendations": [], "unevidenceable": [_refusal("checkout-action")]}

    result = recommend_tests(obligations, [], _change_set(), _client_returning(response))

    assert result.recommendations == []
    assert [r.obligation_id for r in result.unevidenceable] == ["checkout-action"]
    assert result.unevidenceable[0].reason == "a property of a CI step, not of any test"
    # The criterion travels with the refusal, so a reader never has to join it
    # back to the obligation list by id to know what was declined.
    assert result.unevidenceable[0].criterion == "The checkout action is not on Node 20"


def test_an_omitted_obligation_still_aborts_even_when_others_are_declined():
    """The guard's original purpose, preserved. Silence must stay rejected — a
    response that answers neither way is indistinguishable from a truncated one,
    which is exactly the confusion #266 was diagnosed through.

    Three weak obligations — one recommended, one declined, one passed over in
    silence. The two answered ones are what make it a real test: a stage that
    accepted the response because *something* came back for *someone* would
    pass a two-obligation version of this."""
    obligations = [
        _obligation("daily-rate", "Daily rate uses days_in_month", "nominally_supported"),
        _obligation("checkout-action", "The checkout action is not on Node 20", "unsupported"),
        _obligation("proration", "Proration handles partial months", "unsupported"),
    ]
    response = {
        "recommendations": [_recommendation("daily-rate")],
        "unevidenceable": [_refusal("checkout-action")],
    }

    with pytest.raises(SchemaValidationError) as excinfo:
        recommend_tests(obligations, [], _change_set(), _client_returning(response))

    message = str(excinfo.value)
    assert "proration" in message
    assert "1 of 3" in message
    # The two that WERE answered are not swept into the complaint.
    assert "daily-rate" not in message
    assert "checkout-action" not in message


def test_an_obligation_both_recommended_for_and_declined_is_rejected():
    """The two lists are different answers, so an obligation in both is a
    response contradicting itself. Rejected rather than resolved by precedence:
    picking one would report a judgement the model did not make."""
    obligations = [_obligation("daily-rate", "Daily rate uses days_in_month", "unsupported")]
    response = {
        "recommendations": [_recommendation("daily-rate")],
        "unevidenceable": [_refusal("daily-rate")],
    }

    with pytest.raises(SchemaValidationError, match="both recommended for and declined"):
        recommend_tests(obligations, [], _change_set(), _client_returning(response))


def test_a_refusal_naming_an_obligation_the_call_did_not_supply_is_rejected():
    """The same guarantee the recommendation list already had. A refusal is a
    judgement about a specific criterion, so one aimed at an id the call never
    offered is unusable by construction, not merely unmatched."""
    obligations = [_obligation("daily-rate", "Daily rate uses days_in_month", "unsupported")]
    response = {
        "recommendations": [_recommendation("daily-rate")],
        "unevidenceable": [_refusal("invented-id")],
    }

    with pytest.raises(SchemaValidationError, match="did not supply as weak"):
        recommend_tests(obligations, [], _change_set(), _client_returning(response))


def test_a_duplicate_refusal_is_rejected():
    obligations = [_obligation("daily-rate", "Daily rate uses days_in_month", "unsupported")]
    response = {
        "recommendations": [],
        "unevidenceable": [_refusal("daily-rate"), _refusal("daily-rate", "again")],
    }

    with pytest.raises(SchemaValidationError, match="declined more than once"):
        recommend_tests(obligations, [], _change_set(), _client_returning(response))


def test_the_refusal_schema_constrains_ids_to_the_obligations_supplied():
    """Constrained decoding covers the new list too. Without it the refusal
    would be the one place in the stage where a provider honouring the schema
    could still mint an id, and the wrong criterion would be recorded as
    unevidenceable — a false clean on a real gap."""
    from tests.support import client_capturing_schemas

    obligations = [_obligation("daily-rate", "Daily rate uses days_in_month", "unsupported")]
    client, seen = client_capturing_schemas(
        {"recommendations": [], "unevidenceable": [_refusal("daily-rate")]}
    )

    recommend_tests(obligations, [], _change_set(), client)

    refusal_id = seen[0]["properties"]["unevidenceable"]["items"]["properties"]["obligation_id"]
    assert refusal_id["enum"] == ["daily-rate"]


def test_two_runs_over_the_same_obligations_produce_the_same_refusals():
    """Determinism, and specifically not by way of the model repeating itself:
    both output lists are built by walking the weak obligations in order, so the
    order the response happened to use cannot reach the review state."""
    obligations = [
        _obligation("checkout-action", "The checkout action is not on Node 20", "unsupported"),
        _obligation("ruff-pin", "Dev dependencies pin an exact ruff version", "unsupported"),
    ]
    # The response lists them in the opposite order to the obligations.
    response = {
        "recommendations": [],
        "unevidenceable": [_refusal("ruff-pin"), _refusal("checkout-action")],
    }

    first = recommend_tests(obligations, [], _change_set(), _client_returning(response))
    second = recommend_tests(obligations, [], _change_set(), _client_returning(response))

    assert [r.to_dict() for r in first.unevidenceable] == [
        r.to_dict() for r in second.unevidenceable
    ]
    assert [r.obligation_id for r in first.unevidenceable] == ["checkout-action", "ruff-pin"]
