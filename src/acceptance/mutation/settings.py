"""When the execution tier runs, and under what budgets.

**The review decides whether running the project's tests is worth doing; nobody
is asked to switch it on** — the human's ruling of 2026-09-18. An operator flag
was the wrong shape for the question: the person running a review has no way to
know whether a run would produce anything, and the review does.

`decide_execution` is that decision, and it is recorded with its reason rather
than taken silently, because "we did not run the tests" and "we ran them and
found nothing" are different facts about a review.

The rule turns on **whether anything consumes the result**, which is not the
same as whether the result could count as evidence. While edit verification is
off, every observation an injection run makes is recorded as not counted (the
tier gate, DR-171's addendum of 2026-09-16) — but since #340 a run still earns
its keep by deciding which defect-and-test pairs are worth a model call, which
needs no verified edit because it produces no verdict. So the run is worth doing
whenever **either** consumer is switched on, and worth nothing when both are off.

One further consumer would make a run worth doing and does not exist yet: the
coverage prefilter over the same control run (#336). The feasibility probe (#42,
M8.1) is a different question — whether a run can work, not whether it is worth
doing — and will sit in front of this.

Every value here is configuration with a conservative default and none is read
from the project under review (DR-170 Decision 6). This repository exhibits none
of the four classes §8.3 names as infeasible, so it can supply counterexamples
but never thresholds.
"""

from __future__ import annotations

from acceptance.execution.sandbox import SandboxConfig
from acceptance.model_base import PersistableModel as _Model
from acceptance.mutation.runner import (
    DEFAULT_BREADTH_FLOOR,
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_MAX_FAILING_FRACTION,
)
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
    # How many candidate edits to ask for per defect before recording that no
    # usable edit came out of them (#334). One restores the behaviour before
    # #334, for comparison; each extra candidate costs a model call and, if it
    # passes the checks, a test run.
    max_candidates: int = DEFAULT_MAX_CANDIDATES
    # Whether a model call checks that each observed edit really makes its
    # defect true. Off: measured on #45's review it refused 77% of bad edits but
    # also 26% of good ones, and about a quarter of what it let through would
    # still be wrong (DR-171, revision of 2026-09-16). With it off nothing
    # reaches `DEFECT_KILLED`, which is why it also decides whether running is
    # worth doing at all.
    verify_edits: bool = False
    # Whether the injection run is allowed to decide which defect-and-test pairs
    # are worth a model call (#340). On, because the pair judgement is the cost
    # of a review — 1,330 of 1,394 calls and $10.09 of $11.59 on #45's Gate 2 run
    # 3 — and this is the only consumer of the run that pays for itself today.
    # Off runs the review the way it ran before, for comparison.
    route_pairs: bool = True
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
    if not settings.verify_edits and not settings.route_pairs:
        return ExecutionDecision(
            run=False,
            reason=(
                "the project's tests were not run: no result could have counted. Edit "
                "verification is off, so every observation would have been recorded as not "
                "counted, and pair routing is off too, so nothing else consumes the run. "
                "See #335 for the check that would make injection earn its evidence."
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
    earns = "edit verification is on, so an observation can count"
    if not settings.verify_edits:
        earns = (
            "pair routing is on, so an observation can decide which pairs are worth a "
            "model call — it still cannot count as evidence, because edit verification "
            "is off"
        )
    return ExecutionDecision(
        run=True,
        reason=(
            f"the project's tests were run: {defects_with_regions} enumerated defect(s) "
            f"name an editable region and {earns}"
        ),
    )
