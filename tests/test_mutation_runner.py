"""The orchestration: every defect ends with exactly one accounted-for outcome.

These drive the real sandbox against a tiny throwaway project, so the run is
genuine rather than stubbed. Only the descriptor step — the one part that calls
a model — is supplied as a stub, which is what lets the wiring be covered
without a transcript.

The fixture is the amortization case from
`tests/fixtures/archetypes/03-superficial-test` in miniature: a payment function
whose only test asserts the list length and that values are positive, never the
amounts. A defect in the payment formula survives it; a defect in the count
does not. That is #45's Acceptance in small.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from acceptance.evidence_tier import EvidenceTier
from acceptance.execution.outcome import SandboxRunResult, TestOutcome, TestOutcomeKind
from acceptance.execution.sandbox import SandboxConfig
from acceptance.mutation.attempt import (
    DeclineKind,
    DescriptorDecline,
    MutationDescriptor,
    MutationOutcomeKind,
)
from acceptance.mutation.baseline import Baseline, SetAsideTest, establish_baseline
from acceptance.mutation.runner import run_mutations
from acceptance.review_state import ChangeSet, Defect, DefectSet, DefectType, DiffHunk, FileChange

LOAN = '''def amortize(principal, months):
    """Equal monthly payments."""
    payment = principal / months
    return [payment for _ in range(months)]
'''

TEST_LOAN = """from loan import amortize


def test_returns_a_payment_for_each_month():
    schedule = amortize(1200.0, 12)
    assert isinstance(schedule, list)
    assert len(schedule) == 12
    assert all(payment > 0 for payment in schedule)
"""

TEST_ID = "test_loan.py::test_returns_a_payment_for_each_month"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "loan.py").write_text(LOAN, encoding="utf-8")
    (root / "test_loan.py").write_text(TEST_LOAN, encoding="utf-8")
    return root


@pytest.fixture
def change_set() -> ChangeSet:
    # loan.py#0 covers the whole four-line file at head.
    return ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="loan.py",
                status="added",
                category="source",
                hunks=[
                    DiffHunk(
                        header="@@ -0,0 +1,4 @@",
                        old_start=0,
                        old_lines=0,
                        new_start=1,
                        new_lines=4,
                        content=LOAN,
                    )
                ],
            )
        ],
    )


def _defect(defect_id: str, refs: list[str] | None = None) -> Defect:
    return Defect(
        id=defect_id,
        obligation_id="o1",
        type=DefectType.OTHER,
        description="the payments are wrong",
        code_refs=["loan.py#0"] if refs is None else refs,
    )


def _sets(*defects: Defect) -> list[DefectSet]:
    return [DefectSet(obligation_id="o1", defects=list(defects))]


def _builder(replacement: str, *, start: int = 3, end: int = 3):
    def build(_defect, _regions, _sources):
        return MutationDescriptor(
            path="loan.py",
            start_line=start,
            end_line=end,
            replacement=replacement,
            region_label="loan.py#0",
        )

    return build


@pytest.fixture
def green(project: Path) -> Baseline:
    baseline = establish_baseline([TEST_ID], project)
    assert baseline.usable_tests == [TEST_ID], baseline.set_aside
    return baseline


class TestTheTwoOutcomesThatSettle:
    def test_a_defect_the_test_does_not_notice_survives(self, project, change_set, green):
        """The payment amount is wrong, and the test only checks length and
        positivity. This is the static "looks weak" becoming an observed "does
        not discriminate"."""
        attempts = run_mutations(
            _sets(_defect("d-wrong-amount")),
            change_set,
            project,
            green,
            _builder("    payment = principal / months * 3\n"),
        )
        (attempt,) = attempts
        assert attempt.outcome is MutationOutcomeKind.SURVIVED
        assert attempt.killing_tests == []
        assert attempt.tests_run == [TEST_ID]

    def test_a_defect_the_test_does_notice_is_killed(self, project, change_set, green):
        """The count is wrong, and the test asserts the count."""
        attempts = run_mutations(
            _sets(_defect("d-one-short")),
            change_set,
            project,
            green,
            _builder("    return [payment for _ in range(months - 1)]\n", start=4, end=4),
        )
        (attempt,) = attempts
        assert attempt.outcome is MutationOutcomeKind.KILLED
        assert attempt.killing_tests == [TEST_ID]

    def test_both_outcomes_are_reachable_in_one_run(self, project, change_set, green):
        """A runner that reported survival for everything would pass the first
        case and fail here, which is why #45's Acceptance needs both."""

        def build(defect, _regions, _sources):
            if defect.id == "d-one-short":
                return MutationDescriptor(
                    path="loan.py",
                    start_line=4,
                    end_line=4,
                    replacement="    return [payment for _ in range(months - 1)]\n",
                    region_label="loan.py#0",
                )
            return MutationDescriptor(
                path="loan.py",
                start_line=3,
                end_line=3,
                replacement="    payment = principal / months * 3\n",
                region_label="loan.py#0",
            )

        attempts = run_mutations(
            _sets(_defect("d-wrong-amount"), _defect("d-one-short")),
            change_set,
            project,
            green,
            build,
        )
        # Looked up by id rather than by position: attempts come back sorted by
        # defect id, so the order is not the order the defects were given.
        by_id = {a.defect_id: a.outcome for a in attempts}
        assert by_id == {
            "d-wrong-amount": MutationOutcomeKind.SURVIVED,
            "d-one-short": MutationOutcomeKind.KILLED,
        }

    def test_the_injected_text_is_recorded(self, project, change_set, green):
        attempts = run_mutations(
            _sets(_defect("d-wrong-amount")),
            change_set,
            project,
            green,
            _builder("    payment = principal / months * 3\n"),
        )
        assert attempts[0].descriptor is not None
        assert "* 3" in attempts[0].descriptor.replacement


class TestEveryDefectIsAccountedFor:
    def test_a_defect_naming_no_region_is_not_mutable(self, project, change_set, green):
        attempts = run_mutations(
            _sets(_defect("d-absent", refs=[])),
            change_set,
            project,
            green,
            _builder("x"),
        )
        (attempt,) = attempts
        assert attempt.outcome is MutationOutcomeKind.NOT_MUTABLE
        assert "absence defect" in attempt.reason

    def test_a_descriptor_the_builder_declines_is_not_mutable(self, project, change_set, green):
        attempts = run_mutations(
            _sets(_defect("d1")),
            change_set,
            project,
            green,
            lambda _d, _r, _s: None,
        )
        assert attempts[0].outcome is MutationOutcomeKind.NOT_MUTABLE
        assert "no single contiguous edit" in attempts[0].reason

    @pytest.mark.parametrize(
        ("kind", "outcome"),
        [
            (DeclineKind.ALREADY_PRESENT, MutationOutcomeKind.ALREADY_PRESENT),
            (DeclineKind.NOT_A_CODE_PROPERTY, MutationOutcomeKind.NOT_A_CODE_PROPERTY),
            (DeclineKind.NOT_ONE_CONTIGUOUS_EDIT, MutationOutcomeKind.NOT_MUTABLE),
        ],
    )
    def test_a_typed_decline_becomes_its_outcome_with_the_model_s_reason(
        self, project, change_set, green, kind, outcome
    ):
        decline = DescriptorDecline(kind=kind, reason="the model's own words")
        attempts = run_mutations(
            _sets(_defect("d1")), change_set, project, green, lambda _d, _r, _s: decline
        )
        assert attempts[0].outcome is outcome
        assert attempts[0].reason == "the model's own words"
        assert attempts[0].tier is EvidenceTier.STATIC

    def test_an_invalid_descriptor_is_not_mutable_with_the_check_s_reason(
        self, project, change_set, green
    ):
        # Line 9 is outside the named region and past the end of the file.
        attempts = run_mutations(
            _sets(_defect("d1")),
            change_set,
            project,
            green,
            _builder("x = 1\n", start=9, end=9),
        )
        assert attempts[0].outcome is MutationOutcomeKind.NOT_MUTABLE
        assert attempts[0].reason

    def test_every_defect_gets_exactly_one_attempt(self, project, change_set, green):
        attempts = run_mutations(
            _sets(_defect("d1"), _defect("d2"), _defect("d3", refs=[])),
            change_set,
            project,
            green,
            _builder("    payment = principal / months * 3\n"),
        )
        assert [a.defect_id for a in attempts] == ["d1", "d2", "d3"]


class TestWhenInjectionMayNotRun:
    def test_a_baseline_with_no_usable_test_attempts_nothing(self, project, change_set):
        """There is no halt any more: a red candidate test is set aside and the
        rest carry on. The only case where nothing can be observed is a baseline
        that offers no usable test at all."""
        empty = Baseline(
            set_aside=[
                SetAsideTest(
                    test_id=TEST_ID,
                    kind=TestOutcomeKind.FAILED,
                    reason="already red against the code as delivered",
                )
            ]
        )
        attempts = run_mutations(_sets(_defect("d1")), change_set, project, empty, _builder("x"))
        assert attempts[0].outcome is MutationOutcomeKind.NOT_ATTEMPTED
        assert "no candidate test survived the control run" in attempts[0].reason

    def test_no_usable_test_attempts_nothing(self, project, change_set):
        attempts = run_mutations(
            _sets(_defect("d1")), change_set, project, Baseline(), _builder("x")
        )
        assert attempts[0].outcome is MutationOutcomeKind.NOT_ATTEMPTED
        assert "nothing a mutant could be observed against" in attempts[0].reason

    def test_the_defect_is_still_named_when_nothing_ran(self, project, change_set):
        attempts = run_mutations(
            _sets(_defect("d1"), _defect("d2")), change_set, project, Baseline(), _builder("x")
        )
        assert [a.defect_id for a in attempts] == ["d1", "d2"]


class TestAMutantThatBreaksTheModule:
    """The case that would inflate the rating if it were read as a kill.

    A mutant can be valid Python and still stop the module loading. Every test
    that imports it then fails — and if those were recorded as red tests, the
    defect would be credited as killed by all of them, pushing the criterion
    toward `strongly_supported` while nothing had actually been tested.

    It does not happen, because a module that fails to load fails during
    pytest's collection, before any test runs, so the per-test reporting hook
    never fires and the tests come back not started. That is load-bearing
    behaviour of the sandbox, which is why it is pinned here rather than left
    to hold by accident.
    """

    def test_it_is_not_attempted_rather_than_killed(self, project, change_set, green):
        attempts = run_mutations(
            _sets(_defect("d-import-break")),
            change_set,
            project,
            green,
            _builder('raise RuntimeError("boom")\n', start=1, end=4),
        )
        (attempt,) = attempts
        assert attempt.outcome is MutationOutcomeKind.NOT_ATTEMPTED
        assert attempt.killing_tests == []

    def test_the_reason_names_the_cause(self, project, change_set, green):
        attempts = run_mutations(
            _sets(_defect("d-import-break")),
            change_set,
            project,
            green,
            _builder('raise RuntimeError("boom")\n', start=1, end=4),
        )
        assert "none of the 1 candidate tests ran at all" in attempts[0].reason
        assert "breaks the module rather than its behavior" in attempts[0].reason

    def test_it_stays_at_the_static_tier(self, project, change_set, green):
        """So the defect is handed to the static judge rather than counted as
        covered by execution."""
        attempts = run_mutations(
            _sets(_defect("d-import-break")),
            change_set,
            project,
            green,
            _builder('raise RuntimeError("boom")\n', start=1, end=4),
        )
        assert attempts[0].settled is False
        assert attempts[0].tier is EvidenceTier.STATIC


class TestAnEditThatUsesANameThatDoesNotExist:
    """The case the module-level check above cannot see: the file still parses
    and still imports, and the undefined name only fails when a test calls the
    function. Every such test then fails with `NameError`, which says nothing
    about the defect. #45's `gpt-5.4` audit found 7 kills of this shape."""

    def _undefined_name(self):
        return _builder("    payment = principal / months * RATE_TABLE[0]\n")

    def test_it_is_not_counted_as_a_kill(self, project, change_set, green):
        (attempt,) = run_mutations(
            _sets(_defect("d-undefined")), change_set, project, green, self._undefined_name()
        )
        assert attempt.outcome is MutationOutcomeKind.NOT_MUTABLE
        assert attempt.killing_tests == []
        assert attempt.tier is EvidenceTier.STATIC

    def test_the_reason_names_the_exception(self, project, change_set, green):
        (attempt,) = run_mutations(
            _sets(_defect("d-undefined")), change_set, project, green, self._undefined_name()
        )
        assert "NameError" in attempt.reason

    def test_the_edit_and_the_tests_run_are_still_recorded(self, project, change_set, green):
        """So a reader can see what the broken edit was."""
        (attempt,) = run_mutations(
            _sets(_defect("d-undefined")), change_set, project, green, self._undefined_name()
        )
        assert attempt.descriptor is not None
        assert attempt.tests_run == [TEST_ID]


class TestTheFailureTypeIsRecorded:
    def test_an_assertion_failure_is_recorded_as_one(self, project):
        """The control for the check above: an ordinary kill must not look
        broken, or every real kill would be discarded."""
        from acceptance.execution.sandbox import run_tests

        (project / "loan.py").write_text(
            LOAN.replace("range(months)", "range(months - 1)"), encoding="utf-8"
        )
        (outcome,) = run_tests([TEST_ID], project).outcomes
        assert outcome.kind is TestOutcomeKind.FAILED
        assert outcome.error_type == "AssertionError"

    def test_a_real_kill_is_still_a_kill(self, project, change_set, green):
        (attempt,) = run_mutations(
            _sets(_defect("d-one-short")),
            change_set,
            project,
            green,
            _builder("    return [payment for _ in range(months - 1)]\n", start=4, end=4),
        )
        assert attempt.outcome is MutationOutcomeKind.KILLED


class TestBrokenEditRuleNeedsEveryFailure:
    """Decided by the reading of the sandbox result alone, so driven directly.
    One test failing on its own assertion is a real observation about the
    defect, and the rule must not throw it away."""

    def _result(self, *error_types):
        return SandboxRunResult(
            outcomes=[
                TestOutcome(test_id=f"t::{i}", kind=TestOutcomeKind.FAILED, error_type=error_type)
                for i, error_type in enumerate(error_types)
            ]
        )

    def _classify(self, result):
        from acceptance.mutation.runner import _classify

        descriptor = _builder("x\n")(None, None, None)
        tests = [outcome.test_id for outcome in result.outcomes]
        return _classify(_defect("d1"), descriptor, tests, result)

    def test_all_name_errors_is_not_a_kill(self):
        assert self._classify(self._result("NameError", "ImportError")).outcome is (
            MutationOutcomeKind.NOT_MUTABLE
        )

    def test_one_assertion_among_name_errors_is_a_kill(self):
        attempt = self._classify(self._result("NameError", "AssertionError"))
        assert attempt.outcome is MutationOutcomeKind.KILLED

    def test_an_unknown_exception_type_is_a_kill(self):
        """A failure pytest recorded no type for is not assumed broken."""
        assert self._classify(self._result(None)).outcome is MutationOutcomeKind.KILLED


class TestTheBreadthCheck:
    """Breadth, not exception type. A real injected defect can fail with a
    `TypeError`, but it fails a handful of nearby tests; an edit that breaks
    something shared fails far more. Calibrated on #45's own review, where real
    kills failed at most 23 of 339 candidate tests."""

    def _classify(self, failed: int, candidates: int, error_type: str = "TypeError"):
        from acceptance.mutation.runner import _classify

        outcomes = [
            TestOutcome(test_id=f"t::{i}", kind=TestOutcomeKind.FAILED, error_type=error_type)
            for i in range(failed)
        ] + [
            TestOutcome(test_id=f"t::{i}", kind=TestOutcomeKind.PASSED)
            for i in range(failed, candidates)
        ]
        result = SandboxRunResult(outcomes=outcomes)
        descriptor = _builder("x\n")(None, None, None)
        return _classify(_defect("d1"), descriptor, [o.test_id for o in outcomes], result)

    def test_the_largest_real_kill_measured_is_still_a_kill(self):
        assert self._classify(23, 339).outcome is MutationOutcomeKind.KILLED

    def test_the_widest_crashers_measured_are_not_kills(self):
        for failed in (26, 29, 79):
            attempt = self._classify(failed, 339)
            assert attempt.outcome is MutationOutcomeKind.NOT_MUTABLE, failed
            assert attempt.killing_tests == []

    def test_it_ignores_the_exception_type(self):
        """An `AssertionError` failing 79 tests is as broad as a `TypeError`."""
        assert self._classify(79, 339, "AssertionError").outcome is MutationOutcomeKind.NOT_MUTABLE

    def test_the_reason_gives_the_count(self):
        assert "79 of the 339 candidate tests failed" in self._classify(79, 339).reason

    def test_a_small_suite_keeps_a_kill_below_the_floor(self):
        """7.5% of 20 is 1.5; without the floor a 3-test kill would be dropped."""
        assert self._classify(3, 20).outcome is MutationOutcomeKind.KILLED

    def test_the_settings_reach_the_runner(self, project, change_set, green):
        """Wiring: a threshold passed to `run_mutations` is the one applied. The
        one candidate test fails under this edit; with the floor at 0 and any
        fraction below 100% that is too broad."""
        (attempt,) = run_mutations(
            _sets(_defect("d-one-short")),
            change_set,
            project,
            green,
            _builder("    return [payment for _ in range(months - 1)]\n", start=4, end=4),
            max_failing_fraction=0.5,
            breadth_floor=0,
        )
        assert attempt.outcome is MutationOutcomeKind.NOT_MUTABLE


class TestWhenTheProjectsTestsCannotBeRun:
    """The obvious case, and the one §8.3 is about: if the tests cannot run,
    the review falls back to reading code. There is no trade-off to weigh —
    injection is impossible, so the static judge takes everything.

    Driven with an interpreter that does not exist, which is the cheapest way to
    make a real project unrunnable without inventing a fixture for each of
    §8.3's four infeasible classes.
    """

    BROKEN = SandboxConfig(interpreter="/nonexistent/python")

    def test_the_control_run_reports_rather_than_raising(self, project):
        baseline = establish_baseline([TEST_ID], project, self.BROKEN)
        assert baseline.usable_tests == []

    def test_an_unrunnable_test_is_set_aside_with_its_own_reason(self, project):
        """A test the run could not complete is not a red test. It is set aside
        for a different reason, which is what keeps "could not run" — the case
        §8.3 says to degrade on — apart from "is broken"."""
        baseline = establish_baseline([TEST_ID], project, self.BROKEN)
        assert [test.test_id for test in baseline.set_aside] == [TEST_ID]
        assert baseline.failing_tests == []

    def test_every_defect_falls_back_rather_than_being_decided(self, project, change_set):
        baseline = establish_baseline([TEST_ID], project, self.BROKEN)
        attempts = run_mutations(
            _sets(_defect("d1"), _defect("d2")),
            change_set,
            project,
            baseline,
            _builder("    payment = principal / months * 3\n"),
            self.BROKEN,
        )
        assert [a.outcome for a in attempts] == [
            MutationOutcomeKind.NOT_ATTEMPTED,
            MutationOutcomeKind.NOT_ATTEMPTED,
        ]

    def test_the_fallback_is_at_the_static_tier_with_a_reason(self, project, change_set):
        baseline = establish_baseline([TEST_ID], project, self.BROKEN)
        (attempt,) = run_mutations(
            _sets(_defect("d1")),
            change_set,
            project,
            baseline,
            _builder("x"),
            self.BROKEN,
        )
        assert attempt.tier is EvidenceTier.STATIC
        assert attempt.reason
        assert attempt.settled is False

    def test_no_mutant_is_built_so_no_descriptor_is_asked_for(self, project, change_set):
        """The fallback is reached before any model call, so an unrunnable
        project costs nothing extra rather than paying for edits nobody can
        observe."""
        asked = []

        def build(defect, _regions, _sources):
            asked.append(defect.id)

        baseline = establish_baseline([TEST_ID], project, self.BROKEN)
        run_mutations(_sets(_defect("d1")), change_set, project, baseline, build, self.BROKEN)
        assert asked == []


class TestTheOriginalProjectIsNeverTouched:
    def test_the_working_tree_survives_injection(self, project, change_set, green):
        run_mutations(
            _sets(_defect("d1")),
            change_set,
            project,
            green,
            _builder("    payment = principal / months * 3\n"),
        )
        assert (project / "loan.py").read_text(encoding="utf-8") == LOAN
