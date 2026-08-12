"""M5.2 acceptance: per criterion, judge whether the mapped tests would fail
under a named plausible defect — a non-discriminating input is judged
non-discriminating with the specific reason; a genuinely strong test is judged
discriminating.

Discrimination is a schema-constrained model call; per the replay-first
invariant these tests inject the recorded response — no live calls. Prompt
quality (that the *model* judges archetype #4's /30 input non-discriminating)
is verified by a live RECORD run, shown in the PR, not here.
"""

from acceptance.evidence.discrimination import judge_discrimination
from acceptance.review_state import (
    ChangeSet,
    DiffHunk,
    FileChange,
    Obligation,
    ObligationType,
    TestEvidence,
)
from tests.support import client_returning


def _obligation(obligation_id: str, description: str) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=description,
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="...",
    )


def _evidence(identifier: str, obligation_ids: list[str], assertions: list[str]) -> TestEvidence:
    return TestEvidence(
        identifier=identifier,
        location=identifier.split("::", 1)[0],
        assertions=assertions,
        mapped_obligations=obligation_ids,
    )


def _change_set() -> ChangeSet:
    hunk = DiffHunk(
        header="@@ -1 +1 @@",
        old_start=1,
        old_lines=1,
        new_start=1,
        new_lines=1,
        content="+def prorate(...): ...",
    )
    return ChangeSet(
        base_revision="b",
        head_revision="h",
        files=[FileChange(path="billing.py", status="modified", category="source", hunks=[hunk])],
    )


def _exploding_client():
    import tempfile
    from acceptance.llm import Mode, ModelClient, TranscriptStore

    def boom(**kwargs):
        raise AssertionError("no criterion had a mapped test; no model call should be made")

    return ModelClient(
        model="x", mode=Mode.RECORD, store=TranscriptStore(tempfile.mkdtemp()), completion_fn=boom
    )


def test_non_discriminating_input_is_judged_non_discriminating_with_a_reason():
    obligations = [_obligation("daily-rate", "Daily rate is price / days_in_month")]
    evidence = [
        _evidence(
            "test_billing.py::test_half", ["daily-rate"], ["assert prorate(30.0, 15, 30) == 15.0"]
        )
    ]
    response = {
        "obligations": [
            {
                "obligation_id": "daily-rate",
                "defects": [
                    {
                        "description": "hard-code the divisor as / 30 instead of / days_in_month",
                        "would_be_caught": False,
                        "reason": "the test uses a 30-day month, so /30 and /days_in_month coincide (both give 15.0)",
                    },
                ],
            },
        ]
    }

    result = judge_discrimination(obligations, evidence, _change_set(), client_returning(response))

    assert len(result) == 1
    assert result[0].obligation_id == "daily-rate"
    assert result[0].discriminating is False
    assert result[0].defects[0].would_be_caught is False
    assert "coincide" in result[0].defects[0].reason


def test_a_caught_defect_makes_the_criterion_discriminating():
    obligations = [_obligation("daily-rate", "Daily rate is price / days_in_month")]
    evidence = [
        _evidence(
            "test_billing.py::test_strong", ["daily-rate"], ["assert prorate(31.0, 10, 31) == 10.0"]
        )
    ]
    response = {
        "obligations": [
            {
                "obligation_id": "daily-rate",
                "defects": [
                    {
                        "description": "hard-code the divisor as / 30",
                        "would_be_caught": True,
                        "reason": "for a 31-day month /30 gives 10.33, not 10.0, so the test fails under the defect",
                    },
                ],
            },
        ]
    }

    result = judge_discrimination(obligations, evidence, _change_set(), client_returning(response))

    assert result[0].discriminating is True


def test_discriminating_is_true_if_any_defect_is_caught():
    obligations = [_obligation("ob-1", "A")]
    evidence = [_evidence("t.py::test_a", ["ob-1"], ["assert f() == 1"])]
    response = {
        "obligations": [
            {
                "obligation_id": "ob-1",
                "defects": [
                    {"description": "d1", "would_be_caught": False, "reason": "."},
                    {"description": "d2", "would_be_caught": True, "reason": "."},
                ],
            },
        ]
    }

    result = judge_discrimination(obligations, evidence, _change_set(), client_returning(response))

    assert result[0].discriminating is True


def test_criteria_without_mapped_tests_are_not_judged():
    obligations = [_obligation("ob-1", "A"), _obligation("ob-2", "B")]
    # Only ob-1 has a mapped test.
    evidence = [_evidence("t.py::test_a", ["ob-1"], ["assert f() == 1"])]
    response = {
        "obligations": [
            {
                "obligation_id": "ob-1",
                "defects": [
                    {"description": "d", "would_be_caught": True, "reason": "."},
                ],
            },
        ]
    }

    result = judge_discrimination(obligations, evidence, _change_set(), client_returning(response))

    assert {r.obligation_id for r in result} == {"ob-1"}


def test_no_mapped_tests_makes_no_model_call():
    obligations = [_obligation("ob-1", "A")]

    result = judge_discrimination(obligations, [], _change_set(), _exploding_client())

    assert result == []


def test_an_obligation_the_model_omits_is_conservatively_non_discriminating():
    obligations = [_obligation("ob-1", "A"), _obligation("ob-2", "B")]
    evidence = [
        _evidence("t.py::test_a", ["ob-1"], ["assert f() == 1"]),
        _evidence("t.py::test_b", ["ob-2"], ["assert g() == 2"]),
    ]
    # Model only addressed ob-1.
    response = {
        "obligations": [
            {
                "obligation_id": "ob-1",
                "defects": [
                    {"description": "d", "would_be_caught": True, "reason": "."},
                ],
            },
        ]
    }

    result = judge_discrimination(obligations, evidence, _change_set(), client_returning(response))

    by_id = {r.obligation_id: r for r in result}
    assert by_id["ob-1"].discriminating is True
    # ob-2 was omitted -> no defects -> not shown to discriminate.
    assert by_id["ob-2"].discriminating is False
    assert by_id["ob-2"].defects == []
