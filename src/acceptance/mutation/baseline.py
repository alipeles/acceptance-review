"""The control run: the candidate tests against the code as delivered.

A test that already fails at head tells you nothing when it fails under a
mutant, so this run is what makes every later result mean anything. DR-171
Decision 6.

It is not the product grading the user's green suite, which §8.2's scope
boundary rules out, and three things keep that distinction real. No finding is
produced *about* a failing test beyond the fact that it was set aside or that
the review halted. Only candidate tests are consulted, never the suite, so the
product never forms a view on whether the project as a whole passes. And the
halt is a refusal to spend, not a verdict on the change.

**Why a red test halts rather than degrading.** Falling back to the static pair
judgement does not save money — it spends more, because that judgement is the
expensive half and this whole tier exists to avoid it. Spending it on a change
whose own tests are failing buys a review resting on tests that do not pass.
Stopping is the cheap honest answer, and the override is there because a
deliberately parked failure is a real situation.

This is also distinct from §8.3's graceful degradation, which covers a suite
that *cannot* be run and answers by degrading silently to a lower tier. A suite
that runs and fails is the one case where continuing costs more than stopping.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator

from acceptance.execution.outcome import SandboxRunResult, TestOutcomeKind
from acceptance.execution.sandbox import SandboxConfig, run_tests
from acceptance.model_base import PersistableModel as _Model

__all__ = ["Baseline", "SetAsideTest", "establish_baseline"]


class SetAsideTest(_Model):
    """One candidate test that takes no part in any later conclusion, and why.

    Two different things arrive here and the reason is what keeps them apart: a
    test that ran and failed, and a test the run could not complete. Only the
    first is what the halt gate is about.
    """

    test_id: str
    kind: TestOutcomeKind
    reason: str


class Baseline(_Model):
    """What the control run established.

    `usable_tests` is the set every mutant is then run against. A test missing
    from it is missing from every later verdict, which is why `set_aside` records
    each one rather than letting it disappear.
    """

    usable_tests: list[str] = Field(default_factory=list)
    set_aside: list[SetAsideTest] = Field(default_factory=list)
    halted: bool = False
    halt_reason: str = ""

    @property
    def failing_tests(self) -> list[SetAsideTest]:
        """Those set aside because they ran and failed, not because the run
        could not complete them."""
        return [test for test in self.set_aside if test.kind is TestOutcomeKind.FAILED]

    @model_validator(mode="after")
    def _a_halt_says_why(self) -> Baseline:
        has_reason = bool(self.halt_reason.strip())
        if self.halted and not has_reason:
            raise ValueError("a halted review must say why it stopped")
        if not self.halted and has_reason:
            raise ValueError("a review that did not halt carries no halt reason")
        return self

    @model_validator(mode="after")
    def _a_halted_baseline_offers_no_tests(self) -> Baseline:
        if self.halted and self.usable_tests:
            raise ValueError(
                "a halted baseline offers usable tests, which would let injection run "
                "against a control the review already rejected"
            )
        return self


def establish_baseline(
    test_ids: list[str],
    project_root: Path,
    config: SandboxConfig | None = None,
    *,
    allow_failing_tests: bool = False,
) -> Baseline:
    """Run `test_ids` unmutated and decide whether injection may proceed.

    With `allow_failing_tests` false — the default — a single failing candidate
    test halts the review. With it true, the failures are set aside by name and
    the rest carry on.

    A test the run could not complete never halts. That is a feasibility
    outcome rather than a red test, it is #42's (M8.1, the feasibility probe)
    question rather than this one's, and treating "could not run" as "is broken"
    would stop the review on a slow machine.
    """
    requested = list(dict.fromkeys(test_ids))
    if not requested:
        return Baseline()

    result = run_tests(requested, project_root, config)
    return _read(result, allow_failing_tests=allow_failing_tests)


def _read(result: SandboxRunResult, *, allow_failing_tests: bool) -> Baseline:
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
            )
        )

    failing = [test for test in set_aside if test.kind is TestOutcomeKind.FAILED]
    if failing and not allow_failing_tests:
        names = ", ".join(test.test_id for test in failing)
        return Baseline(
            set_aside=set_aside,
            halted=True,
            halt_reason=(
                f"{len(failing)} candidate test(s) fail against the code as delivered "
                f"({names}). A test that is already red says nothing when it goes red under "
                "an injected defect, so nothing would be learned by continuing. Re-run "
                "allowing failing tests to proceed with these set aside."
            ),
        )

    return Baseline(usable_tests=usable, set_aside=set_aside)
