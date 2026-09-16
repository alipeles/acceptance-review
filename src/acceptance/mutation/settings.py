"""Whether the execution tier runs, and under what budgets.

**Off by default, and opted into explicitly.** Two reasons, and the first is the
one that will change. §8.3 makes execution optional and conditional on a
feasibility probe; #42 (M8.1) is that probe and does not exist yet, so nothing
can currently decide on a project's behalf whether its tests may be run. Until
it does, the operator decides. The second reason is narrower: a review that
silently started running a project's tests would be a surprising thing for a
static checker to do on first acquaintance.

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

__all__ = ["ExecutionSettings", "ReviewHalted"]


class ExecutionSettings(_Model):
    """How the mutation stage behaves, or that it does not run at all.

    `allow_failing_tests` is the override on DR-171 Decision 6's gate. With it
    false — the default — a candidate test that is red against the code as
    delivered halts the review, because falling back to the static pair
    judgement costs *more* than stopping and buys a review resting on tests that
    do not pass. With it true, the failures are set aside by name and the rest
    carries on, which is what a project with a deliberately parked failure
    needs.
    """

    enabled: bool = False
    allow_failing_tests: bool = False
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
    # reaches `DEFECT_KILLED`.
    verify_edits: bool = False
    sandbox: SandboxConfig = SandboxConfig()


class ReviewHalted(Exception):
    """The control run found a candidate test already failing, and stopped.

    An exception rather than a `Review` carrying a flag, because there is no
    review to return: the halt happens before the stages that would produce a
    verdict, and that is the whole point — the expensive half is what is being
    declined. A `Review` saying "no findings" would be indistinguishable from a
    clean one.

    Carries the `Baseline` so the caller can name the failing tests rather than
    only report that some existed.
    """

    def __init__(self, baseline) -> None:
        super().__init__(baseline.halt_reason)
        self.baseline = baseline
