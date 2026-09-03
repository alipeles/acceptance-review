"""The outcome record's own rules, independent of running anything."""

import pytest

from acceptance.execution.outcome import (
    COMPLETED_KINDS,
    SandboxRunResult,
    TestOutcome,
    TestOutcomeKind,
)


def _passed(test_id="tests/test_a.py::test_one"):
    return TestOutcome(test_id=test_id, kind=TestOutcomeKind.PASSED)


@pytest.mark.parametrize(
    "kind",
    [
        TestOutcomeKind.NETWORK_BLOCKED,
        TestOutcomeKind.TIMED_OUT,
        TestOutcomeKind.NOT_STARTED,
    ],
)
def test_an_outcome_that_did_not_complete_must_say_why(kind):
    with pytest.raises(ValueError, match="must carry a reason"):
        TestOutcome(test_id="tests/test_a.py::test_one", kind=kind)


@pytest.mark.parametrize(
    "kind",
    [
        TestOutcomeKind.NETWORK_BLOCKED,
        TestOutcomeKind.TIMED_OUT,
        TestOutcomeKind.NOT_STARTED,
    ],
)
def test_a_blank_reason_does_not_count_as_a_reason(kind):
    with pytest.raises(ValueError, match="must carry a reason"):
        TestOutcome(test_id="tests/test_a.py::test_one", kind=kind, reason="   ")


@pytest.mark.parametrize("kind", sorted(COMPLETED_KINDS, key=lambda k: k.value))
def test_a_completed_outcome_needs_no_reason_and_may_not_carry_one(kind):
    outcome = TestOutcome(test_id="tests/test_a.py::test_one", kind=kind)
    assert outcome.completed

    with pytest.raises(ValueError, match="completed, so it carries no reason"):
        TestOutcome(test_id="tests/test_a.py::test_one", kind=kind, reason="ran to the end")


def test_only_passed_and_failed_count_as_completed():
    assert COMPLETED_KINDS == {TestOutcomeKind.PASSED, TestOutcomeKind.FAILED}
    blocked = TestOutcome(
        test_id="tests/test_a.py::test_one",
        kind=TestOutcomeKind.NETWORK_BLOCKED,
        reason="reached for the network",
    )
    assert not blocked.completed


def test_a_test_cannot_hold_two_outcomes():
    with pytest.raises(ValueError, match="more than one outcome"):
        SandboxRunResult(outcomes=[_passed(), _passed()])


def test_an_aborted_run_must_say_why_it_stopped():
    with pytest.raises(ValueError, match="must say why it stopped"):
        SandboxRunResult(outcomes=[_passed()], aborted=True)


def test_a_run_that_was_not_aborted_carries_no_abort_reason():
    with pytest.raises(ValueError, match="carries no abort reason"):
        SandboxRunResult(outcomes=[_passed()], abort_reason="stopped")


def test_completed_outcomes_excludes_everything_the_run_could_not_observe():
    result = SandboxRunResult(
        outcomes=[
            _passed("tests/test_a.py::test_one"),
            TestOutcome(
                test_id="tests/test_a.py::test_two",
                kind=TestOutcomeKind.NOT_STARTED,
                reason="the run ended first",
            ),
        ]
    )
    assert [o.test_id for o in result.completed_outcomes] == ["tests/test_a.py::test_one"]
    assert result.outcome_for("tests/test_a.py::test_two").kind is (TestOutcomeKind.NOT_STARTED)
    assert result.outcome_for("tests/test_a.py::absent") is None
