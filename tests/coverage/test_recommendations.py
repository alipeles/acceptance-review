"""M7.1 acceptance: an uncovered defect earns a §9.5 structured recommendation
with every field populated — the non-discriminating daily-rate case (archetype
#4).

**The unit is a defect, not a weak criterion** (#316, DR-312 decision 4). What
the stage is given is every enumerated way the change could fail a criterion
that no candidate test was judged to fail on; what it returns is one prescription
per such defect. Two failures stop being possible rather than becoming checks:
prescribing a test that already exists (#250, #287), because a covered defect is
never in the input; and a prescription resting on nothing traceable (#283),
because `TestRecommendation.defect_id` is required.

Generation is a schema-constrained model call; per the replay-first invariant
these tests inject the recorded response via completion_fn — no live calls.
Recommendation *quality* against the real model is shown by the PR's record run.
"""

import pytest

from acceptance.coverage.recommendations import recommend_tests
from acceptance.llm import SchemaValidationError
from acceptance.review_state import (
    ChangeSet,
    Defect,
    DefectSet,
    DiffHunk,
    FileChange,
    Obligation,
    ObligationType,
    PairVerdict,
    RequiredEvidence,
)
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import client_returning as _client_returning


def _obligation(obligation_id: str, description: str) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=description,
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior=description,
    )


def _defect(obligation_id: str, slug: str, description: str) -> Defect:
    return Defect(
        id=f"{obligation_id}/{slug}",
        obligation_id=obligation_id,
        type="other",
        description=description,
        code_refs=["billing.py#0"],
    )


def _defect_set(obligation_id: str, *defects: Defect) -> DefectSet:
    return DefectSet(obligation_id=obligation_id, defects=list(defects))


def _kills(defect_id: str, test_id: str = "test_billing.py::test_half_month") -> PairVerdict:
    return PairVerdict(defect_id=defect_id, test_id=test_id, kills=True, reason="it asserts on it")


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
        raise AssertionError("a model call was issued with no uncovered defects")

    return ModelClient(
        model="x", mode=Mode.RECORD, store=TranscriptStore(tempfile.mkdtemp()), completion_fn=boom
    )


def _answer(defect_id: str) -> dict:
    return {
        "defect_id": defect_id,
        "required_inputs": "a month whose length is not 30",
        "boundary_conditions": "0 days and a full month",
        "expected_output": "price/28*days",
        "required_assertions": ["assert prorate(280, 14, 28) == 140.0"],
        "repo_conventions": "test_billing.py",
    }


_HARD_CODED_30 = "hard-codes price/30 instead of price/days_in_month"


def _archetype_4():
    """Archetype #4's daily-rate gap: the only test uses a 30-day month, where
    price/days_in_month and a hard-coded price/30 give the same answer."""
    obligation = _obligation("daily-rate", "Daily rate is monthly_price divided by days_in_month")
    defect = _defect("daily-rate", "divides-by-thirty", _HARD_CODED_30)
    return [obligation], [_defect_set("daily-rate", defect)], defect


def test_an_uncovered_defect_gets_a_fully_populated_recommendation():
    obligations, defect_sets, defect = _archetype_4()
    response = {
        "recommendations": [
            {
                "defect_id": defect.id,
                "required_inputs": "A month whose length is not 30, e.g. days_in_month=28.",
                "boundary_conditions": "0 days used and a full month.",
                "expected_output": "prorate(28*price, 14, 28) uses price/28, not price/30.",
                "required_assertions": ["assert prorate(280, 14, 28) == 140.0"],
                "repo_conventions": "add to test_billing.py alongside test_half_of_a_month",
            }
        ]
    }

    recommendations = recommend_tests(
        obligations, defect_sets, [], _change_set(), _client_returning(response)
    ).recommendations

    assert len(recommendations) == 1
    rec = recommendations[0]
    assert rec.obligation_id == "daily-rate"
    assert rec.defect_id == defect.id
    assert rec.criterion == "Daily rate is monthly_price divided by days_in_month"
    # Every §9.5 field is populated.
    assert rec.required_inputs
    assert rec.boundary_conditions
    assert rec.expected_output
    assert rec.required_assertions
    assert rec.repo_conventions


def test_the_plausible_defect_is_copied_from_the_record_not_restated_by_the_model():
    """§9.5 field 6 is the enumerated defect itself, so a green run of the
    prescribed test demonstrably closes *that* gap (§8.4).

    The response carries no `plausible_defect` at all — asking for a
    restatement bought a paraphrase that could drift from the record it was
    meant to name, and cost output on every prescription.
    """
    obligations, defect_sets, defect = _archetype_4()
    rec = recommend_tests(
        obligations,
        defect_sets,
        [],
        _change_set(),
        _client_returning({"recommendations": [_answer(defect.id)]}),
    ).recommendations[0]

    assert rec.plausible_defect == _HARD_CODED_30


def test_a_recommendation_citing_no_defect_record_is_unrepresentable():
    """#283's shape, removed by the type rather than checked for.

    That review prescribed a test on a basis nothing in the record supported, so
    a reader could not follow the prescription back to the criterion text it was
    meant to serve. `defect_id` is required, and the `Defect` it names carries
    the `obligation_id` and the `code_refs`, so the trail from prescription to
    criterion to exact lines exists by construction (§13.6).
    """
    from pydantic import ValidationError

    from acceptance.review_state import TestRecommendation

    with pytest.raises(ValidationError) as raised:
        TestRecommendation(
            obligation_id="daily-rate",
            criterion="Daily rate is monthly_price divided by days_in_month",
            required_inputs="a 28-day month",
            boundary_conditions="none",
            expected_output="price/28",
            required_assertions=["assert prorate(280, 14, 28) == 140.0"],
            plausible_defect="hard-codes /30",
            repo_conventions="test_billing.py",
        )

    assert "defect_id" in str(raised.value)


def test_every_recommendation_a_run_produces_names_a_defect_the_review_holds():
    """The type stops a recommendation with no defect id. It cannot stop one
    naming an id that belongs to no record, which would break the same trail one
    step further along — so the stage is checked to emit only ids it was given.
    """
    obligations, defect_sets, defect = _archetype_4()
    known = {d.id for s in defect_sets for d in s.defects}

    result = recommend_tests(
        obligations,
        defect_sets,
        [],
        _change_set(),
        _client_returning({"recommendations": [_answer(defect.id)]}),
    )

    assert result.recommendations
    for rec in result.recommendations:
        assert rec.defect_id in known


def test_a_defect_a_test_would_fail_on_earns_no_recommendation_and_no_model_call():
    """#250 and #287 made structural. The covered defect is not merely dropped
    from the output — with nothing uncovered, no call is issued at all, so a
    redundant prescription has nothing to be composed from."""
    obligations, defect_sets, defect = _archetype_4()

    result = recommend_tests(
        obligations, defect_sets, [_kills(defect.id)], _change_set(), _exploding_client()
    )

    assert result.recommendations == []
    assert result.unobtained == []


def test_a_criterion_with_no_enumerated_defects_earns_no_recommendation():
    """A reasoned-empty enumeration says no plausible defect exists. There is
    nothing to prescribe a test for, and prescribing one would demand evidence
    of a failure nobody believes can happen."""
    obligations = [_obligation("true-by-construction", "The type makes this unrepresentable")]
    defect_sets = [
        DefectSet(
            obligation_id="true-by-construction",
            defects=[],
            reason="no change to this criterion can fail it",
        )
    ]

    result = recommend_tests(obligations, defect_sets, [], _change_set(), _exploding_client())

    assert result.recommendations == []
    assert result.unobtained == []


def test_recommendation_round_trips_through_persistence():
    obligations, defect_sets, defect = _archetype_4()
    from acceptance.review_state import TestRecommendation

    rec = recommend_tests(
        obligations,
        defect_sets,
        [],
        _change_set(),
        _client_returning({"recommendations": [_answer(defect.id)]}),
    ).recommendations[0]
    assert TestRecommendation.from_dict(rec.to_dict()) == rec


def _two_uncovered():
    """Two criteria, one uncovered defect each."""
    obligations = [
        _obligation("daily-rate", "Daily rate uses days_in_month"),
        _obligation("proration", "Proration handles partial months"),
    ]
    defect_sets = [
        _defect_set("daily-rate", _defect("daily-rate", "d1", "the daily rate is wrong")),
        _defect_set("proration", _defect("proration", "d1", "proration is wrong")),
    ]
    return obligations, defect_sets


def test_a_response_skipping_a_defect_records_it_as_not_obtained():
    """The "always" half of the invariant, kept — but paid for with one defect
    instead of the whole review (#275).

    #218 made a skipped item visible by raising, which was right about the
    visibility and wrong about the price: on a real run one omission out of
    thirteen discarded twelve honoured prescriptions, the verdict, and every
    finding the earlier stages had produced. The omission is still refused a
    silent pass — it becomes an explicit not-obtained record — and the answers
    that did come back survive.
    """
    obligations, defect_sets = _two_uncovered()
    response = {"recommendations": [_answer("daily-rate/d1")]}
    log = UnusableAnswerLog()

    result = recommend_tests(
        obligations, defect_sets, [], _change_set(), _client_returning(response), log
    )

    assert [r.defect_id for r in result.recommendations] == ["daily-rate/d1"]
    assert [u.defect_id for u in result.unobtained] == ["proration/d1"]
    # Not merely present: it names the defect and the criterion and says the
    # answer was never obtained, so a reader cannot mistake it for a complete one.
    unobtained = result.unobtained[0]
    assert unobtained.obligation_id == "proration"
    assert unobtained.criterion == "Proration handles partial months"
    assert "no prescription was produced" in unobtained.reason
    # And the evidence axis is told, which is what keeps the verdict honest.
    assert log.indeterminate_obligations == {"proration"}


def test_one_criterion_can_be_answered_for_twice_and_missed_once():
    """The reason the omission record is keyed on the defect rather than the
    criterion. Three uncovered defects under ONE criterion, two answered: a
    record keyed on the criterion could not represent this at all, and would
    either lose the omission or wrongly mark the whole criterion unanswered.
    """
    obligations = [_obligation("daily-rate", "Daily rate uses days_in_month")]
    defect_sets = [
        _defect_set(
            "daily-rate",
            _defect("daily-rate", "d1", "wrong divisor"),
            _defect("daily-rate", "d2", "wrong rounding"),
            _defect("daily-rate", "d3", "negative days accepted"),
        )
    ]
    response = {"recommendations": [_answer("daily-rate/d1"), _answer("daily-rate/d3")]}

    result = recommend_tests(
        obligations, defect_sets, [], _change_set(), _client_returning(response)
    )

    assert [r.defect_id for r in result.recommendations] == ["daily-rate/d1", "daily-rate/d3"]
    assert [u.defect_id for u in result.unobtained] == ["daily-rate/d2"]


def test_several_answers_survive_an_omission_and_several_omissions_are_each_recorded():
    """The two-defect case cannot separate "keeps the answers" from "keeps the
    one answer", and cannot show that a second omission is recorded rather than
    the first standing for both.

    Four defects: two answered, two skipped, and the two skipped ones are not
    adjacent in the supplied order — so an implementation that stopped at the
    first gap, or that recorded one entry per response rather than per defect,
    fails here and passes the smaller case.
    """
    obligations = [
        _obligation("daily-rate", "Daily rate uses days_in_month"),
        _obligation("proration", "Proration handles partial months"),
        _obligation("rounding", "Totals round half up"),
        _obligation("credits", "Credits offset the next invoice"),
    ]
    defect_sets = [
        _defect_set(name, _defect(name, "d1", f"{name} is wrong"))
        for name in ("daily-rate", "proration", "rounding", "credits")
    ]
    response = {"recommendations": [_answer("daily-rate/d1"), _answer("rounding/d1")]}
    log = UnusableAnswerLog()

    result = recommend_tests(
        obligations, defect_sets, [], _change_set(), _client_returning(response), log
    )

    assert [r.defect_id for r in result.recommendations] == ["daily-rate/d1", "rounding/d1"]
    # In supplied order, not response order and not "the first one we noticed".
    assert [u.defect_id for u in result.unobtained] == ["credits/d1", "proration/d1"]
    assert log.indeterminate_obligations == {"proration", "credits"}


def test_an_omission_does_not_mark_the_answered_criteria_indeterminate():
    """The other half of the same guarantee: a positive answer we could honour
    keeps its judgment. Marking the whole call indeterminate would discard
    twelve good prescriptions in a different way."""
    obligations, defect_sets = _two_uncovered()
    response = {"recommendations": [_answer("daily-rate/d1")]}
    log = UnusableAnswerLog()

    recommend_tests(obligations, defect_sets, [], _change_set(), _client_returning(response), log)

    assert "daily-rate" not in log.indeterminate_obligations


def test_a_response_naming_a_defect_the_call_did_not_supply_is_rejected():
    """The "only" half. Enforcing it by dropping the entry is the same silence
    in the other direction: a recommendation the call never asked for means the
    model answered about something else, and that is worth knowing."""
    obligations, defect_sets = _two_uncovered()
    response = {
        "recommendations": [
            _answer("daily-rate/d1"),
            _answer("proration/d1"),
            _answer("some-other-defect"),
        ]
    }

    with pytest.raises(SchemaValidationError) as raised:
        recommend_tests(obligations, defect_sets, [], _change_set(), _client_returning(response))

    assert "some-other-defect" in str(raised.value)


def test_a_duplicate_recommendation_is_rejected():
    obligations, defect_sets = _two_uncovered()
    response = {
        "recommendations": [
            _answer("daily-rate/d1"),
            _answer("daily-rate/d1"),
            _answer("proration/d1"),
        ]
    }

    with pytest.raises(SchemaValidationError) as raised:
        recommend_tests(obligations, defect_sets, [], _change_set(), _client_returning(response))

    assert "more than once" in str(raised.value)


def test_every_uncovered_defect_gets_exactly_one_recommendation_in_a_fixed_order():
    """The invariant stated positively, and in supplied order rather than
    response order — two recorded runs over one input must be byte-identical."""
    obligations, defect_sets = _two_uncovered()
    response = {"recommendations": [_answer("proration/d1"), _answer("daily-rate/d1")]}

    result = recommend_tests(
        obligations, defect_sets, [], _change_set(), _client_returning(response)
    )

    assert [r.defect_id for r in result.recommendations] == ["daily-rate/d1", "proration/d1"]
    assert result.unobtained == []


def test_two_runs_over_one_omitting_response_produce_identical_state():
    """Determinism over this path: the not-obtained record is derived from the
    supplied set and the response, both fixed, so nothing about it may vary
    between runs (M0.5)."""
    obligations, defect_sets = _two_uncovered()
    response = {"recommendations": [_answer("daily-rate/d1")]}

    first = recommend_tests(
        obligations, defect_sets, [], _change_set(), _client_returning(response)
    )
    second = recommend_tests(
        obligations, defect_sets, [], _change_set(), _client_returning(response)
    )

    assert [u.to_dict() for u in first.unobtained] == [u.to_dict() for u in second.unobtained]
    assert [r.to_dict() for r in first.recommendations] == [
        r.to_dict() for r in second.recommendations
    ]


def test_more_defects_than_the_batch_size_are_split_across_calls():
    """The unit got smaller when it became a defect, so the count got larger —
    #314's Gate 2 enumerated 75 defects for one review. A single call for all of
    them is the shape DR-164 warns about, and the response here is six fields of
    prose per item, which is output and never amortizes under the input-only
    caching discount.
    """
    obligations = [_obligation("daily-rate", "Daily rate uses days_in_month")]
    defect_sets = [
        _defect_set(
            "daily-rate",
            *[_defect("daily-rate", f"d{index}", f"way {index}") for index in range(1, 6)],
        )
    ]
    calls: list[list[str]] = []

    def completion_fn(**kwargs):
        import json

        from tests.support import _fake_response, _supplied_enum

        # The batch's work list, read off the constrained schema it sent, so the
        # double answers each call completely without being told the split.
        offered = _supplied_enum("defect_id", **kwargs)
        calls.append(list(offered))
        return _fake_response(
            json.dumps({"recommendations": [_answer(defect_id) for defect_id in offered]})
        )

    from tests.support import model_client_with

    result = recommend_tests(
        obligations,
        defect_sets,
        [],
        _change_set(),
        model_client_with(completion_fn),
        batch_size=2,
    )

    assert [len(offered) for offered in calls] == [2, 2, 1]
    assert len(result.recommendations) == 5
    assert result.unobtained == []


# --- #153: no test is prescribed for a boundary obligation --------------------


def test_no_test_is_recommended_for_a_code_evidence_only_obligation():
    """#153's acceptance, and #146's original complaint. The exclusion
    "Converting the rest of the suite is out of scope" was rated
    partially_supported and earned a test recommendation — but there is no
    behavioural test for "we didn't also do something else", so the prescription
    named evidence that cannot exist.

    The exploding client is the assertion that matters: a boundary obligation's
    defects must not merely be dropped from the output, they must not reach the
    model at all. A call that ran and returned nothing would pass a check on the
    result alone while still costing a call and a transcript.
    """
    boundary = Obligation(
        id="pagination",
        description="The change does not alter how the invoice list is paginated",
        type=ObligationType.INVARIANT,
        importance="critical",
        explicit=True,
        observable_behavior="pagination code appearing in the diff",
        required_evidence=RequiredEvidence.CODE_ONLY,
        required_evidence_reason="no test can assert that excluded work was not done",
        satisfied_by_absence=True,
    )
    defect_sets = [_defect_set("pagination", _defect("pagination", "d1", "pagination changed"))]

    result = recommend_tests([boundary], defect_sets, [], _change_set(), _exploding_client())

    assert result.recommendations == []
    # And it is not recorded as not-obtained either: nothing was asked about it,
    # so there is no missing answer. #266's decision that no test is owed here
    # is a settled answer, not an absent one.
    assert result.unobtained == []


def test_a_weak_ordinary_obligation_alongside_a_boundary_one_still_recommends():
    """The boundary the test above cannot draw on its own: filtering must remove
    the boundary obligation's defects from the batch without suppressing the
    real gap sitting next to it. Asserting the recommendation names the ordinary
    criterion, not merely that something came back."""
    ordinary = _obligation("daily-rate", "Daily rate is monthly_price divided by days_in_month")
    boundary = Obligation(
        id="pagination",
        description="The change does not alter how the invoice list is paginated",
        type=ObligationType.INVARIANT,
        importance="critical",
        explicit=True,
        observable_behavior="pagination code appearing in the diff",
        required_evidence=RequiredEvidence.CODE_ONLY,
        required_evidence_reason="no test can assert that excluded work was not done",
        satisfied_by_absence=True,
    )
    defect_sets = [
        _defect_set("daily-rate", _defect("daily-rate", "d1", "hard-codes /30")),
        _defect_set("pagination", _defect("pagination", "d1", "pagination changed")),
    ]

    result = recommend_tests(
        [ordinary, boundary],
        defect_sets,
        [],
        _change_set(),
        _client_returning({"recommendations": [_answer("daily-rate/d1")]}),
    )

    assert [r.obligation_id for r in result.recommendations] == ["daily-rate"]
    assert result.unobtained == []
