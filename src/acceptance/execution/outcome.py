"""What a sandboxed run observed about each test it was asked about.

Every requested test ends with exactly one outcome. An outcome that is not a
completed run carries a reason, following DR-171 Decision 8 (the mutation
record's outcome vocabulary) and `DefectSet`'s rule about empty sets: "looked
and could not" and "did not look" are different, and only one of them is a
defect in the tool. A test that silently disappears from the result is
indistinguishable from one that passed, which is the failure this module
exists to prevent.
"""

from __future__ import annotations

from enum import Enum

from pydantic import model_validator

from acceptance.model_base import PersistableModel as _Model

__all__ = [
    "COMPLETED_KINDS",
    "SandboxRunResult",
    "TestOutcome",
    "TestOutcomeKind",
]


class TestOutcomeKind(str, Enum):
    """The five things that can become of a test the runner was asked about."""

    # Not a pytest test class. The name is the domain's, and pytest collects any
    # class whose name starts with "Test" unless told otherwise.
    __test__ = False

    PASSED = "passed"
    FAILED = "failed"
    NETWORK_BLOCKED = "network_blocked"
    TIMED_OUT = "timed_out"
    NOT_STARTED = "not_started"


#: The kinds that mean the test ran to completion and the run observed its
#: verdict. Only these may be read as evidence about the test itself; the rest
#: say something about the run.
COMPLETED_KINDS = frozenset({TestOutcomeKind.PASSED, TestOutcomeKind.FAILED})


class TestOutcome(_Model):
    """One test's result, with a reason whenever it did not complete."""

    # See TestOutcomeKind: keeps pytest from collecting a domain model.
    __test__ = False

    test_id: str
    kind: TestOutcomeKind
    reason: str | None = None

    @property
    def completed(self) -> bool:
        return self.kind in COMPLETED_KINDS

    @model_validator(mode="after")
    def _reason_accompanies_every_incomplete_outcome(self) -> TestOutcome:
        has_reason = bool((self.reason or "").strip())
        if not self.completed and not has_reason:
            raise ValueError(
                f"outcome {self.kind.value} for {self.test_id!r} must carry a reason: "
                "a test the runner tried and could not complete has to stay "
                "distinguishable from one it never tried"
            )
        if self.completed and has_reason:
            raise ValueError(
                f"outcome {self.kind.value} for {self.test_id!r} completed, so it carries no reason"
            )
        return self


class SandboxRunResult(_Model):
    """Every requested test's outcome, plus why the run stopped if it did.

    `aborted` is set when the whole-run time budget expired. It is not an error:
    the tests that did complete keep their outcomes, and the rest are
    `not_started`.
    """

    outcomes: list[TestOutcome]
    aborted: bool = False
    abort_reason: str | None = None

    @property
    def completed_outcomes(self) -> list[TestOutcome]:
        return [outcome for outcome in self.outcomes if outcome.completed]

    def outcome_for(self, test_id: str) -> TestOutcome | None:
        for outcome in self.outcomes:
            if outcome.test_id == test_id:
                return outcome
        return None

    @model_validator(mode="after")
    def _one_outcome_per_test(self) -> SandboxRunResult:
        seen: set[str] = set()
        for outcome in self.outcomes:
            if outcome.test_id in seen:
                raise ValueError(f"{outcome.test_id!r} has more than one outcome")
            seen.add(outcome.test_id)
        return self

    @model_validator(mode="after")
    def _abort_reason_accompanies_abort(self) -> SandboxRunResult:
        has_reason = bool((self.abort_reason or "").strip())
        if self.aborted and not has_reason:
            raise ValueError("an aborted run must say why it stopped")
        if not self.aborted and has_reason:
            raise ValueError("a run that was not aborted carries no abort reason")
        return self
