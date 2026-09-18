"""The control run, and what it does with a test that is already red.

**A failing candidate test is set aside and the rest carry on** — the human's
ruling of 2026-09-18, which reverses DR-171 Decision 6 (revised), where one red
test halted the whole review by default. One test nobody can trust says nothing
about the others, and blocking them on it throws away every observation the run
could still make.

These exercise `_read` against constructed `SandboxRunResult`s rather than
driving pytest, so the reading is tested apart from the sandbox that feeds it;
`test_execution_sandbox.py` covers the run itself.
"""

from __future__ import annotations

import pytest

from acceptance.execution.outcome import SandboxRunResult, TestOutcome, TestOutcomeKind
from acceptance.mutation.baseline import SetAsideTest, establish_baseline
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
        baseline = read_baseline(_result(_passed("t.py::a"), _passed("t.py::b")))
        assert baseline.usable_tests == ["t.py::a", "t.py::b"]
        assert baseline.set_aside == []

    def test_no_tests_requested_is_an_ordinary_result(self, tmp_path):
        """An obligation set with no candidate tests is a result, not a reason
        to stop."""
        baseline = establish_baseline([], tmp_path)
        assert baseline.usable_tests == []


class TestARedTestIsSetAsideAndTheRestCarryOn:
    def test_the_other_tests_stay_usable(self):
        """The ruling, stated as the thing that must not happen: one red test
        must not cost the observations the green ones could still make."""
        baseline = read_baseline(_result(_passed("t.py::a"), _failed("t.py::b")))
        assert baseline.usable_tests == ["t.py::a"]

    def test_the_failing_test_is_not_usable(self):
        """It is already red, so it says nothing when it goes red under an
        injected defect."""
        baseline = read_baseline(_result(_passed("t.py::a"), _failed("t.py::b")))
        assert "t.py::b" not in baseline.usable_tests

    def test_the_failing_test_is_named(self):
        baseline = read_baseline(_result(_failed("t.py::b")))
        assert [test.test_id for test in baseline.set_aside] == ["t.py::b"]

    def test_every_candidate_failing_leaves_nothing_usable(self):
        """Not a halt, and not an error: there is simply nothing to observe
        against, which `run_mutations` already reports per defect."""
        baseline = read_baseline(_result(_failed("t.py::a"), _failed("t.py::b")))
        assert baseline.usable_tests == []
        assert len(baseline.set_aside) == 2

    def test_the_report_can_say_which_were_set_aside_and_why(self):
        baseline = read_baseline(_result(_failed("t.py::b")))
        (entry,) = baseline.set_aside
        assert entry.kind is TestOutcomeKind.FAILED
        assert entry.reason.strip()


class TestTestsThatCouldNotRun:
    """A test the run could not complete is a feasibility outcome, which #42
    (M8.1, the feasibility probe) owns. Treating "could not run" as "is broken"
    would stop the review on a slow machine."""

    def test_it_is_set_aside_like_a_red_one(self):
        baseline = read_baseline(_result(_passed("t.py::a"), _timed_out("t.py::b")))
        assert baseline.usable_tests == ["t.py::a"]
        assert [test.test_id for test in baseline.set_aside] == ["t.py::b"]

    def test_failing_tests_reports_only_the_red_ones(self):
        """The two are set aside alike but mean different things, so the record
        keeps them apart."""
        baseline = read_baseline(_result(_failed("t.py::a"), _timed_out("t.py::b")))
        assert [test.test_id for test in baseline.failing_tests] == ["t.py::a"]
        assert len(baseline.set_aside) == 2

    def test_its_reason_is_the_runs_own(self):
        baseline = read_baseline(_result(_timed_out("t.py::b")))
        assert "budget expired" in baseline.set_aside[0].reason


class TestSetAsideInvariants:
    def test_a_set_aside_test_without_a_reason_is_refused(self):
        """#45's Gate 2 asked for this. The report prints the id and the reason,
        so an empty one turns a disclosure into a bare name — which reads as the
        tool having lost the test rather than deliberately excluded it."""
        with pytest.raises(ValueError, match="set aside with no reason"):
            SetAsideTest(test_id="t.py::a", kind=TestOutcomeKind.FAILED, reason="  ")
