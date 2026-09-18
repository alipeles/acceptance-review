"""When the execution tier runs, and under what budgets.

**The review decides whether running the project's tests is worth doing; nobody
is asked to switch it on** — the human's ruling of 2026-09-18. An operator flag
was the wrong shape for the question: the person running a review has no way to
know whether a run would produce anything, and the review does.

`decide_execution` is that decision, and it is recorded with its reason rather
than taken silently, because "we did not run the tests" and "we ran them and
found nothing" are different facts about a review.

Today the rule turns on **whether any result could count**. While edit
verification is off, every observation an injection run makes is recorded as not
counted (the tier gate, DR-171's addendum of 2026-09-16), so a run spends money
and roughly ten minutes to earn nothing. That is the case the ruling is about.
Two other consumers would each make a run worth doing and neither exists yet:
the coverage prefilter over the same control run (#336) and the feasibility
probe (#42, M8.1).

Every value here is configuration with a conservative default and none is read
from the project under review (DR-170 Decision 6). This repository exhibits none
of the four classes §8.3 names as infeasible, so it can supply counterexamples
but never thresholds.
"""

from __future__ import annotations

from acceptance.execution.sandbox import SandboxConfig
from acceptance.model_base import PersistableModel as _Model
from acceptance.mutation.runner import DEFAULT_BREADTH_FLOOR, DEFAULT_MAX_FAILING_FRACTION
from acceptance.mutation.validity import DEFAULT_MAX_EDIT_LINES
from acceptance.review_state import ExecutionDecision

__all__ = ["ExecutionDecision", "ExecutionSettings", "decide_execution"]


class ExecutionSettings(_Model):
    """The budgets and thresholds the execution tier runs under.

    Note what is *not* here: any field saying whether to run. That is
    `decide_execution`'s answer, computed per review.
    """

    max_edit_lines: int = DEFAULT_MAX_EDIT_LINES
    # The breadth check: no kill is counted when more than this fraction of the
    # candidate tests fail under an edit, and more than `breadth_floor` of them.
    # See `runner.py` for the calibration and its limits.
    max_failing_fraction: float = DEFAULT_MAX_FAILING_FRACTION
    breadth_floor: int = DEFAULT_BREADTH_FLOOR
    # Whether a model call checks that each observed edit really makes its
    # defect true. Off: measured on #45's review it refused 77% of bad edits but
    # also 26% of good ones, and about a quarter of what it let through would
    # still be wrong (DR-171, revision of 2026-09-16). With it off nothing
    # reaches `DEFECT_KILLED`, which is why it also decides whether running is
    # worth doing at all.
    verify_edits: bool = False
    sandbox: SandboxConfig = SandboxConfig()


def decide_execution(
    settings: ExecutionSettings | None, defects_with_regions: int
) -> ExecutionDecision:
    """Decide whether running the project's tests would produce anything.

    Two conditions, and both are about whether a run could yield a result rather
    than about whether it would succeed:

    - **Something must consume the result.** While `verify_edits` is off no
      observation can count, so the run is spent for nothing.
    - **There must be something to inject.** A defect naming no usable region
      cannot be edited, so a review with none of them has nothing to observe.

    `settings` of `None` means a caller that has not configured the tier at all,
    which is not the same as deciding against it — it is the absence of the
    configuration a run needs.
    """
    if settings is None:
        return ExecutionDecision(
            run=False,
            reason=(
                "the review was given no execution settings, so the project's tests were not run"
            ),
        )
    if not settings.verify_edits:
        return ExecutionDecision(
            run=False,
            reason=(
                "the project's tests were not run: no result could have counted. Edit "
                "verification is off, so every observation would have been recorded as not "
                "counted, and nothing else consumes the run. See #335 for the check that "
                "would make injection earn its evidence."
            ),
        )
    if defects_with_regions == 0:
        return ExecutionDecision(
            run=False,
            reason=(
                "the project's tests were not run: no enumerated defect names a changed "
                "region that could be edited, so there was nothing to observe a test "
                "against"
            ),
        )
    return ExecutionDecision(
        run=True,
        reason=(
            f"the project's tests were run: {defects_with_regions} enumerated defect(s) "
            "name an editable region and edit verification is on, so an observation can "
            "count"
        ),
    )
