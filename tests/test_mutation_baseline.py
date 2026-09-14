"""The control run, and the gate that stops a review resting on red tests.

DR-171 Decision 6 as revised. These exercise `_read` against constructed
`SandboxRunResult`s rather than driving pytest, so the gate's logic is tested
apart from the sandbox that feeds it; `test_execution_sandbox.py` covers the
run itself.
"""

from __future__ import annotations

import pytest

from acceptance.execution.outcome import SandboxRunResult, TestOutcome, TestOutcomeKind
from acceptance.mutation.baseline import Baseline, establish_baseline
from acceptance.mutation.baseline import _read as read_baseline


def _result(*outcomes: TestOutcome) -> SandboxRunResult:
    return SandboxRunResult(outcomes=list(outcomes))


def _passed(test_id: str) -> TestOutcome:
    return TestOutcome(test_id=test_id, kind=TestOutcomeKind.PASSED)


def _failed(test_id: str) -> TestOutcome:
    return TestOutcome(test_id=test_id, kind=TestOutcomeKind.FAILED, reason=None)


def _timed_out(test_id: str) -> TestOutcome:
    return TestOutcome(
        test_id=test_id,
        kind=TestOutcomeKind.TIMED_OUT,
        reason="the per-test budget expired",
    )


class TestAGreenBaseline:
    def test_every_passing_test_is_usable(self):
        baseline = read_baseline(
            _result(_passed("t.py::a"), _passed("t.py::b")), allow_failing_tests=False
        )
        assert baseline.usable_tests == ["t.py::a", "t.py::b"]
        assert baseline.set_aside == []
        assert baseline.halted is False

    def test_no_tests_requested_is_not_a_halt(self, tmp_path):
        """An obligation set with no candidate tests is an ordinary result, not
        a reason to stop."""
        baseline = establish_baseline([], tmp_path)
        assert baseline.halted is False
        assert baseline.usable_tests == []


class TestARedBaselineHalts:
    def test_one_failing_test_halts_the_review(self):
        baseline = read_baseline(
            _result(_passed("t.py::a"), _failed("t.py::b")), allow_failing_tests=False
        )
        assert baseline.halted is True
        assert "t.py::b" in baseline.halt_reason

    def test_the_halt_reason_says_why_continuing_would_learn_nothing(self):
        baseline = read_baseline(_result(_failed("t.py::b")), allow_failing_tests=False)
        assert "already red" in baseline.halt_reason
        assert "set aside" in baseline.halt_reason

    def test_a_halted_baseline_offers_no_usable_tests(self):
        """Otherwise injection could run against a control the review has
        already rejected."""
        baseline = read_baseline(
            _result(_passed("t.py::a"), _failed("t.py::b")), allow_failing_tests=False
        )
        assert baseline.usable_tests == []

    def test_the_failing_test_is_still_named(self):
        baseline = read_baseline(_result(_failed("t.py::b")), allow_failing_tests=False)
        assert [test.test_id for test in baseline.set_aside] == ["t.py::b"]


class TestTheOverride:
    def test_a_failing_test_is_set_aside_instead_of_halting(self):
        baseline = read_baseline(
            _result(_passed("t.py::a"), _failed("t.py::b")), allow_failing_tests=True
        )
        assert baseline.halted is False
        assert baseline.usable_tests == ["t.py::a"]
        assert [test.test_id for test in baseline.set_aside] == ["t.py::b"]

    def test_a_set_aside_test_takes_no_part_in_later_conclusions(self):
        baseline = read_baseline(
            _result(_passed("t.py::a"), _failed("t.py::b")), allow_failing_tests=True
        )
        assert "t.py::b" not in baseline.usable_tests

    def test_the_report_can_say_which_were_set_aside_and_why(self):
        baseline = read_baseline(_result(_failed("t.py::b")), allow_failing_tests=True)
        (entry,) = baseline.set_aside
        assert entry.kind is TestOutcomeKind.FAILED
        assert entry.reason.strip()


class TestTestsThatCouldNotRun:
    """A test the run could not complete is a feasibility outcome, which #42
    (M8.1, the feasibility probe) owns. Treating "could not run" as "is broken"
    would stop the review on a slow machine."""

    def test_a_timed_out_test_does_not_halt(self):
        baseline = read_baseline(
            _result(_passed("t.py::a"), _timed_out("t.py::b")), allow_failing_tests=False
        )
        assert baseline.halted is False

    def test_but_it_is_still_set_aside(self):
        baseline = read_baseline(
            _result(_passed("t.py::a"), _timed_out("t.py::b")), allow_failing_tests=False
        )
        assert baseline.usable_tests == ["t.py::a"]
        assert [test.test_id for test in baseline.set_aside] == ["t.py::b"]

    def test_failing_tests_reports_only_the_red_ones(self):
        baseline = read_baseline(
            _result(_failed("t.py::a"), _timed_out("t.py::b")), allow_failing_tests=True
        )
        assert [test.test_id for test in baseline.failing_tests] == ["t.py::a"]
        assert len(baseline.set_aside) == 2

    def test_its_reason_is_the_runs_own(self):
        baseline = read_baseline(_result(_timed_out("t.py::b")), allow_failing_tests=False)
        assert "budget expired" in baseline.set_aside[0].reason


class TestHaltInvariants:
    def test_a_halt_without_a_reason_is_refused(self):
        with pytest.raises(ValueError, match="must say why it stopped"):
            Baseline(halted=True)

    def test_a_reason_without_a_halt_is_refused(self):
        with pytest.raises(ValueError, match="carries no halt reason"):
            Baseline(halt_reason="something")
