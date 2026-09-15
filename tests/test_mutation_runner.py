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
from acceptance.execution.sandbox import SandboxConfig
from acceptance.mutation.attempt import MutationDescriptor, MutationOutcomeKind
from acceptance.mutation.baseline import Baseline, establish_baseline
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
    assert baseline.halted is False, baseline.halt_reason
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
    def test_a_halted_baseline_attempts_nothing(self, project, change_set):
        halted = Baseline(halted=True, halt_reason="a candidate test is red at head")
        attempts = run_mutations(_sets(_defect("d1")), change_set, project, halted, _builder("x"))
        assert attempts[0].outcome is MutationOutcomeKind.NOT_ATTEMPTED
        assert "halted before injection" in attempts[0].reason

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

    def test_an_unrunnable_suite_does_not_halt_the_review(self, project):
        """A test the run could not complete is not a red test. Halting here
        would stop every review on a project whose tests cannot run, which is
        the case §8.3 says to degrade on."""
        baseline = establish_baseline([TEST_ID], project, self.BROKEN)
        assert baseline.halted is False

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
