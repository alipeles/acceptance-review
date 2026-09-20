"""The control run: the candidate tests against the code as delivered.

A test that already fails at head tells you nothing when it fails under a
mutant, so this run is what makes every later result mean anything. DR-171
Decision 6.

It is not the product grading the user's green suite, which §8.2's scope
boundary rules out, and two things keep that distinction real. No finding is
produced *about* a failing test beyond the fact that it was set aside. And only
candidate tests are consulted, never the suite, so the product never forms a
view on whether the project as a whole passes.

**A red test is set aside; it does not stop anything.** The human's ruling of
2026-09-18, reversing DR-171 Decision 6 (revised), where one red candidate test
halted the review by default. That decision argued from cost — falling back to
the static pair judgement spends more than stopping — but cost does not answer
the correctness question. One test nobody can trust says nothing about the
others, and stopping on it throws away every observation the rest could make.

§8.3's graceful degradation is a different case: a suite that *cannot* be run
degrades to a lower tier. A test that runs and fails is simply excluded.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator

from acceptance.execution.outcome import SandboxRunResult, TestOutcome, TestOutcomeKind
from acceptance.execution.sandbox import SandboxConfig, collect_tests, run_tests
from acceptance.model_base import PersistableModel as _Model
from acceptance.mutation.workspace import copied_project

__all__ = ["Baseline", "SetAsideTest", "establish_baseline"]


class SetAsideTest(_Model):
    """One candidate test that takes no part in any later conclusion, and why.

    Two different things arrive here and the reason is what keeps them apart: a
    test that ran and failed, and a test the run could not complete. The second
    is a feasibility outcome, which #42 (M8.1, the feasibility probe) owns.
    """

    test_id: str
    kind: TestOutcomeKind
    reason: str
    # Carried from the `TestOutcome` this was built from, and the reason that
    # matters: `reason` is a sentence this module writes and is therefore the
    # same for every test excluded the same way, while these two say what
    # actually happened to THIS test. Without them a review that set aside 76
    # candidate tests recorded one sentence 76 times, and which tests failed for
    # which reason could not be recovered — the sandbox sends the run's output to
    # `DEVNULL`, so nothing else holds it. Both defaulted, so a review recorded
    # before they existed reads back unchanged.
    error_type: str | None = None
    detail: str | None = None

    @model_validator(mode="after")
    def _the_reason_is_said(self) -> SetAsideTest:
        """A set-aside test with no reason names an exclusion nobody can act on.

        The report prints the id and the reason, so an empty one turns a
        disclosure into a bare name — which reads as the tool having lost track
        of the test rather than having deliberately excluded it. Structural
        here rather than left to `_read` supplying a default, for the same
        reason `TestOutcome` and `MutationAttempt` require theirs.
        """
        if not self.reason.strip():
            raise ValueError(
                f"{self.test_id!r} was set aside with no reason: an exclusion a reader "
                "cannot see the cause of is indistinguishable from a lost test"
            )
        return self


class Baseline(_Model):
    """What the control run established.

    `usable_tests` is the set every mutant is then run against. A test missing
    from it is missing from every later verdict, which is why `set_aside` records
    each one rather than letting it disappear.
    """

    usable_tests: list[str] = Field(default_factory=list)
    set_aside: list[SetAsideTest] = Field(default_factory=list)

    @property
    def failing_tests(self) -> list[SetAsideTest]:
        """Those set aside because they ran and failed, not because the run
        could not complete them."""
        return [test for test in self.set_aside if test.kind is TestOutcomeKind.FAILED]


def establish_baseline(
    test_ids: list[str],
    project_root: Path,
    config: SandboxConfig | None = None,
) -> Baseline:
    """Run `test_ids` unmutated and report which of them injection may use.

    **A test that fails here is set aside, and the rest carry on.** It takes no
    part in any conclusion and the report names it. It does not stop the other
    tests from running and it does not stop the review — the human's ruling of
    2026-09-18, which reverses DR-171 Decision 6 (revised), where a single red
    candidate test halted the review by default. The cost argument that decision
    rested on does not answer the correctness one: one test nobody can trust
    says nothing about the others, and blocking them on it throws away every
    observation the run could still make.

    A test the run could not complete is set aside for its own reason. That is a
    feasibility outcome rather than a red test — #42's (M8.1, the feasibility
    probe) question rather than this one's — and calling "could not run" the same
    thing as "is broken" would mislabel a slow machine.
    """
    requested = list(dict.fromkeys(test_ids))
    if not requested:
        return Baseline()

    # Ask pytest which of these it will admit, BEFORE asking it to run them.
    # Discovery finds test files by walking the repository; pytest decides what
    # is a test by its own rules, and an id it cannot collect makes it exit with
    # a usage error and run nothing at all. One disagreement otherwise costs
    # every test, which is what #45's own Gate 2 hit.
    collectable = collect_tests(requested, project_root, config)
    dropped = [
        SetAsideTest(
            test_id=test_id,
            kind=TestOutcomeKind.NOT_STARTED,
            reason=(
                "the project's own pytest does not collect this test, so asking it to run "
                "would make the whole run fail without running anything. Test discovery "
                "found the file; pytest declines it."
            ),
        )
        for test_id in requested
        if test_id not in collectable
    ]
    runnable = [test_id for test_id in requested if test_id in collectable]

    if not runnable:
        return Baseline(set_aside=dropped)

    result = _observe(runnable, project_root, config)
    baseline = _read(result)
    if baseline.usable_tests:
        baseline = _drop_unfaithful(baseline, project_root, config)
    # The dropped ids go first: they were excluded before anything ran, and a
    # reader scanning the block should meet "never admitted" before "ran and
    # failed".
    return baseline.model_copy(update={"set_aside": dropped + baseline.set_aside})


def _drop_unfaithful(
    baseline: Baseline, project_root: Path, config: SandboxConfig | None
) -> Baseline:
    """Set aside any test that does not behave the same in a copy of the project.

    Every mutant runs in a copy, and the copy leaves things out — version
    control history, caches, dependency trees. A test that depends on one of
    those passes here and fails there, and the difference would be read as the
    injected defect breaking it. **That is a false kill: a finding against the
    builder for something they did not do.**

    So the control is run twice, once in place and once in an unmodified copy,
    and a test that disagrees between them is excluded from every later
    conclusion with the reason recorded. This turns an exclusion list that is
    wrong for some project from a source of false findings into a smaller set of
    usable tests, which is the direction a review should fail in.

    Costs one copy and one extra run of the control set, once per review,
    against one copy and one run per defect afterwards.
    """
    try:
        with copied_project(project_root, prefix="acceptance-control-") as root:
            mirrored = _observe(baseline.usable_tests, root, config)
    except OSError as error:  # the contract is that a baseline returns
        mirrored = SandboxRunResult(
            outcomes=[
                TestOutcome(
                    test_id=test_id,
                    kind=TestOutcomeKind.NOT_STARTED,
                    reason=f"the project could not be copied for the check: {error}",
                )
                for test_id in baseline.usable_tests
            ]
        )

    unfaithful = [
        SetAsideTest(
            test_id=outcome.test_id,
            kind=outcome.kind,
            reason=(
                "the test passes in the project but not in an unmodified copy of it, so a "
                "failure under an injected defect could not be attributed to the defect. "
                f"In the copy it was: {outcome.kind.value}"
            ),
            error_type=outcome.error_type,
            detail=outcome.detail,
        )
        for outcome in mirrored.outcomes
        if outcome.kind is not TestOutcomeKind.PASSED
    ]
    if not unfaithful:
        return baseline

    excluded = {test.test_id for test in unfaithful}
    return baseline.model_copy(
        update={
            "usable_tests": [t for t in baseline.usable_tests if t not in excluded],
            "set_aside": baseline.set_aside + unfaithful,
        }
    )


def _observe(
    runnable: list[str], project_root: Path, config: SandboxConfig | None
) -> SandboxRunResult:
    """Run the candidate tests, falling back to one file at a time if nothing ran.

    **Whether a set of tests can run is a property of the set, not of each test
    in it.** Two modules that each collect alone can collide when collected
    together — one shadows the other's module name, or one's import leaves state
    the other trips over — and pytest then exits with a usage error having run
    nothing at all. The per-test gate in `collect_tests` cannot see that, because
    it asks about each file on its own.

    This is not hypothetical. On this repository, a test belonging to an
    archetype fixture collects perfectly by itself and takes every other
    candidate down when collected beside the real test module whose name it
    shares. That is what left #45's execution tier inert.

    So: run everything, and if the run observed *nothing*, run each file
    separately and keep what each one yields. A file that poisons the combined
    run is then the only thing lost. The fallback costs one process per file and
    fires only when the fast path already failed.

    Deliberately here and not in `run_tests`. A mutation run that observes
    nothing is the ordinary signal that the mutant broke the module, and
    retrying it file by file would spend tens of processes to re-learn something
    the single run already said.
    """
    result = run_tests(runnable, project_root, config)
    by_file = _by_file(runnable)
    if result.completed_outcomes or len(by_file) < 2:
        return result

    outcomes: list[TestOutcome] = []
    for ids in by_file.values():
        outcomes.extend(run_tests(ids, project_root, config).outcomes)
    return SandboxRunResult(outcomes=outcomes)


def _by_file(test_ids: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for test_id in test_ids:
        grouped.setdefault(test_id.split("::", 1)[0], []).append(test_id)
    return grouped


def _read(result: SandboxRunResult) -> Baseline:
    usable: list[str] = []
    set_aside: list[SetAsideTest] = []

    for outcome in result.outcomes:
        if outcome.kind is TestOutcomeKind.PASSED:
            usable.append(outcome.test_id)
            continue
        set_aside.append(
            SetAsideTest(
                test_id=outcome.test_id,
                kind=outcome.kind,
                reason=outcome.reason or "the test failed against the code as delivered",
                error_type=outcome.error_type,
                detail=outcome.detail,
            )
        )

    return Baseline(usable_tests=usable, set_aside=set_aside)
