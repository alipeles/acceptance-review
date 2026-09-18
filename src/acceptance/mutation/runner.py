"""Injects each named defect and records who noticed.

The order is fixed and each step can only end one way, which is what keeps every
defect accounted for: resolve the regions the defect named, ask for a
descriptor, check it mechanically, copy the project, apply, run, read.

**Every candidate test is run against every mutant**, and which ones go red is
the mapping from tests to this defect (DR-171 Decision 4, revised). Nothing
narrows the set first. The one cheap narrowing available — line coverage — was
measured against #316's Gate 2 review and excluded 43 of 268 recorded kills,
because a test can detect a defect through a file read or through behavior
absent from the named lines. Under the original decision each of those became a
*reported finding* that no test covers the defect, not merely a lost
opportunity.

The descriptor step is supplied by the caller rather than imported, because it
is the one part of this module that calls a model. Passing it in is what lets
the whole orchestration be tested against a stub, so the wiring is covered
without a transcript.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from pathlib import Path

from acceptance.concurrency import map_calls
from acceptance.execution.outcome import SandboxRunResult, TestOutcomeKind
from acceptance.execution.sandbox import SandboxConfig, run_tests
from acceptance.mutation.attempt import (
    DECLINE_OUTCOMES,
    AlreadyDefective,
    DescriptorAnswer,
    DescriptorDecline,
    MutationAttempt,
    MutationDescriptor,
    MutationOutcomeKind,
    RepairCorroboration,
)
from acceptance.mutation.baseline import Baseline
from acceptance.mutation.injection import mutated_copy
from acceptance.mutation.region import Region, regions_for
from acceptance.mutation.validity import DEFAULT_MAX_EDIT_LINES, invalidity_reason
from acceptance.review_state import ChangeSet, Defect, DefectSet

__all__ = [
    "BROKEN_EDIT_ERRORS",
    "DEFAULT_BREADTH_FLOOR",
    "DEFAULT_INJECTIONS_IN_FLIGHT",
    "DEFAULT_MAX_FAILING_FRACTION",
    "DescriptorBuilder",
    "run_mutations",
]

#: How many injections run at once. Sized for this machine's cores, because the
#: work is local CPU and disk with no network in it at all — the opposite of the
#: model-call concurrency in `concurrency.py`, whose limit is a provider's rate
#: allowance. Two cores are left for the rest of the review and for the machine.
#:
#: Each injection is a full pytest process over the candidate set, so raising
#: this past the core count makes every run slower without finishing sooner.
DEFAULT_INJECTIONS_IN_FLIGHT = max(1, (os.cpu_count() or 4) - 2)

#: Exceptions that mean an edit broke the code rather than changed its behavior:
#: a name that does not exist, or a module that no longer imports. When EVERY
#: test that failed under an edit failed with one of these, the failures are
#: about the broken edit and not about the defect, so no kill is recorded.
#: `UnboundLocalError` and `ModuleNotFoundError` are listed by name because the
#: match is on the recorded class name, not on the class hierarchy.
BROKEN_EDIT_ERRORS = frozenset(
    {"NameError", "UnboundLocalError", "ImportError", "ModuleNotFoundError"}
)

#: The breadth check. An edit that makes one defect true fails the handful of
#: tests near that defect; an edit that crashes a shared path or disables a
#: feature fails far more. When more than this fraction of the candidate tests
#: fail under an edit, the failures are about the edit's breadth and not about
#: the defect, and no kill is recorded — whatever exception the tests failed on.
#:
#: Calibrated on #45's own review (339 candidate tests, 58 hand-judged kills
#: across audits v5 and v6). Real kills failed at most 23 tests. Edits that broke
#: far more than their defect failed 79, 29, 26, 16, 14 and 12, and the other ten
#: 4 or fewer. 7.5% is 25.4 tests at that size: it keeps every real kill with a
#: margin of two, and catches only the three widest crashers plus three other bad
#: edits (49, 47, 33). **It is a backstop for the extreme cases, not a filter for
#: most bad edits**: breadth does not separate the rest.
#:
#: One suite size only, so this is a conservative default rather than a measured
#: rule, and it is configuration.
DEFAULT_MAX_FAILING_FRACTION = 0.075

#: Below this many failures the breadth check never fires. The fraction alone
#: would demote a genuine kill of 3 tests in a 20-test suite. Not measured — no
#: small suite has been audited — so it errs toward keeping kills.
DEFAULT_BREADTH_FLOOR = 10

#: Given one defect, the regions it named, and the text of each of those files
#: at head, produce the smallest edit that makes the defect true — or a typed
#: decline saying why none does, or `None` when no usable answer came back.
DescriptorBuilder = Callable[
    [Defect, Sequence[Region], dict[str, str]],
    DescriptorAnswer,
]


def run_mutations(
    defect_sets: Sequence[DefectSet],
    change_set: ChangeSet,
    project_root: Path,
    baseline: Baseline,
    build_descriptor: DescriptorBuilder,
    config: SandboxConfig | None = None,
    max_edit_lines: int = DEFAULT_MAX_EDIT_LINES,
    max_in_flight: int = DEFAULT_INJECTIONS_IN_FLIGHT,
    max_failing_fraction: float = DEFAULT_MAX_FAILING_FRACTION,
    breadth_floor: int = DEFAULT_BREADTH_FLOOR,
) -> list[MutationAttempt]:
    """One attempt per defect, sorted by defect id.

    Returns an attempt for every defect, including the ones nothing could be
    done with. A defect missing from this list would be indistinguishable from
    one that survived, which is the failure `MutationAttempt`'s validators exist
    to prevent.
    """
    defects = [defect for defect_set in defect_sets for defect in defect_set.defects]

    if not baseline.usable_tests:
        return [
            _not_attempted(
                defect,
                "no candidate test survived the control run, so there is nothing a mutant "
                "could be observed against",
            )
            for defect in defects
        ]

    # Concurrent, because each injection is independent by construction: its own
    # copy of the project, its own pytest process, no shared state. Serially
    # this stage is one test run per defect end to end — on #45's own review, 58
    # injections of 324 tests each, over an hour of wall clock for work that is
    # entirely parallel.
    #
    # `map_calls` returns in INPUT order, not completion order, which is what
    # keeps two runs over the same input byte-identical (`concurrency.py`, rule
    # 1). No conclusion depends on the order — the rating is computed from sets
    # and counts — but the stored review is a list, and a review that serialises
    # differently on a rerun is one nobody can diff.
    #
    # The limit is `max_in_flight`, which is sized for CPUs rather than borrowed
    # from `concurrency.DEFAULT_MAX_IN_FLIGHT`: that constant is chosen for a
    # provider's rate limit and its own comment says the useful ceiling is "what
    # the provider will accept at once, not how many cores are free". This work
    # is the opposite — no network at all, entirely local CPU and disk.
    attempts = map_calls(
        defects,
        lambda defect: _attempt(
            defect,
            change_set,
            project_root,
            baseline.usable_tests,
            build_descriptor,
            config,
            max_edit_lines,
            _Breadth(max_failing_fraction, breadth_floor),
        ),
        max_in_flight=max(1, max_in_flight),
    )
    # Sorted as well as ordered, so the record does not depend on the pool
    # preserving order at all. Belt and braces: if `map_calls` is ever swapped
    # for something that yields as results complete, this still holds.
    return sorted(attempts, key=lambda attempt: attempt.defect_id)


def _attempt(
    defect: Defect,
    change_set: ChangeSet,
    project_root: Path,
    tests: list[str],
    build_descriptor: DescriptorBuilder,
    config: SandboxConfig | None,
    max_edit_lines: int,
    breadth: _Breadth,
) -> MutationAttempt:
    regions = regions_for(defect, change_set)
    if not regions:
        return _not_mutable(
            defect,
            "the defect names no changed region with text at head, so there is no span to "
            "replace. This is the shape of an absence defect, where the implicated lines are "
            "where behavior should be and is not.",
        )

    try:
        sources = _sources(regions, project_root)
    except OSError as error:
        return _not_mutable(defect, f"a file the defect named could not be read: {error}")

    readable = [region for region in regions if region.path in sources]
    if not readable:
        return _not_mutable(
            defect, "none of the files the defect named exist in the project at head"
        )

    descriptor = build_descriptor(defect, readable, sources)
    if isinstance(descriptor, AlreadyDefective):
        return _already_defective(
            defect,
            descriptor,
            readable,
            sources,
            project_root,
            tests,
            config,
            max_edit_lines,
            breadth,
        )
    if isinstance(descriptor, DescriptorDecline):
        return MutationAttempt(
            defect_id=defect.id,
            outcome=DECLINE_OUTCOMES[descriptor.kind],
            reason=descriptor.reason,
        )
    if descriptor is None:
        return _not_mutable(
            defect, "no single contiguous edit was found that would make this defect true"
        )

    reason = invalidity_reason(
        descriptor, readable, sources.get(descriptor.path, ""), max_edit_lines
    )
    if reason is not None:
        return _not_mutable(defect, reason)

    try:
        with mutated_copy(project_root, descriptor) as root:
            result = run_tests(tests, root, config)
    except OSError as error:
        return MutationAttempt(
            defect_id=defect.id,
            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
            descriptor=descriptor,
            reason=f"the mutated copy could not be prepared: {error}",
        )

    return _classify(defect, descriptor, tests, result, breadth)


class _Breadth:
    """The breadth check's two numbers, passed as one."""

    def __init__(self, max_failing_fraction: float, floor: int) -> None:
        self.max_failing_fraction = max_failing_fraction
        self.floor = floor

    def too_broad(self, failed: int, candidates: int) -> bool:
        """More than the fraction of the candidate tests failed, and more than
        the floor. The candidates are the tests the control run found passing,
        so every failure here is one the edit caused."""
        return failed > self.floor and failed > self.max_failing_fraction * candidates

    def reason(self, failed: int, candidates: int) -> str:
        return (
            f"{failed} of the {candidates} candidate tests failed under the edit, more than "
            f"{self.max_failing_fraction:.1%} of them. An edit that makes one defect true "
            "fails the tests near it; one that fails this many has broken something shared, "
            "so the failures say nothing about the named defect and no kill is counted."
        )


_DEFAULT_BREADTH = _Breadth(DEFAULT_MAX_FAILING_FRACTION, DEFAULT_BREADTH_FLOOR)


def _already_defective(
    defect: Defect,
    claim: AlreadyDefective,
    readable: Sequence[Region],
    sources: dict[str, str],
    project_root: Path,
    tests: list[str],
    config: SandboxConfig | None,
    max_edit_lines: int,
    breadth: _Breadth = _DEFAULT_BREADTH,
) -> MutationAttempt:
    """Record the claim that the code already has the defect, and test its repair.

    The claim is the model's reading of the code and stays at the static tier
    whatever the run shows. Running the candidate tests against the repair only
    says how far a test run supports it:

    - every test passes on the repair too: no test pins the expected behaviour,
      which is consistent with the claim;
    - a test fails on the repair: that test passes on the delivered code and
      fails when the code does the expected behaviour, so it asserts the
      defective one — the stronger finding.

    The same rules that stop an injection being read as a kill apply to the
    repair: it must pass the mechanical checks, a run where every failure is a
    missing name or import says nothing, and a partly observed run with no
    failure proves nothing.
    """

    def finding(corroboration, *, failing=(), note=""):
        reason = claim.reason if not note else f"{claim.reason} ({note})"
        return MutationAttempt(
            defect_id=defect.id,
            outcome=MutationOutcomeKind.ALREADY_PRESENT,
            reason=reason,
            repair=claim.repair,
            repair_corroboration=corroboration,
            repair_failing_tests=list(failing),
        )

    repair = claim.repair
    if repair is None:
        return finding(RepairCorroboration.NOT_RUN, note="no repair edit was given")
    invalid = invalidity_reason(repair, readable, sources.get(repair.path, ""), max_edit_lines)
    if invalid is not None:
        return finding(RepairCorroboration.NOT_RUN, note=f"the repair was refused: {invalid}")
    try:
        with mutated_copy(project_root, repair) as root:
            result = run_tests(tests, root, config)
    except OSError as error:
        return finding(
            RepairCorroboration.NOT_RUN, note=f"the repaired copy could not be prepared: {error}"
        )

    failed = [outcome for outcome in result.outcomes if outcome.kind is TestOutcomeKind.FAILED]
    if failed and all(outcome.error_type in BROKEN_EDIT_ERRORS for outcome in failed):
        return finding(RepairCorroboration.NOT_RUN, note="the repair broke the code")
    if breadth.too_broad(len(failed), len(tests)):
        return finding(
            RepairCorroboration.NOT_RUN,
            note=f"the repair failed {len(failed)} of {len(tests)} candidate tests, too many "
            "to say anything about this defect",
        )
    if failed:
        return finding(
            RepairCorroboration.A_TEST_ASSERTS_DEFECTIVE,
            failing=[outcome.test_id for outcome in failed],
        )
    if any(not outcome.completed for outcome in result.outcomes):
        return finding(
            RepairCorroboration.NOT_RUN, note="the run on the repair was not fully observed"
        )
    return finding(RepairCorroboration.NO_TEST_PINS_EXPECTED)


def _classify(
    defect: Defect,
    descriptor: MutationDescriptor,
    tests: list[str],
    result: SandboxRunResult,
    breadth: _Breadth = _DEFAULT_BREADTH,
) -> MutationAttempt:
    """Read the mutated run as killed, survived, or nothing at all.

    A kill needs one red test. A *survival* needs every requested test to have
    completed, and that asymmetry is deliberate: a survival is the finding that
    the builder's tests are proven weak, so it may not rest on tests nobody
    watched. A partly-observed run that produced no red test is recorded as
    `not_attempted` and handed to the static judge, which is the weaker claim
    and the honest one.
    """
    failed = [outcome for outcome in result.outcomes if outcome.kind is TestOutcomeKind.FAILED]
    killing = [outcome.test_id for outcome in failed]
    if failed and all(outcome.error_type in BROKEN_EDIT_ERRORS for outcome in failed):
        return MutationAttempt(
            defect_id=defect.id,
            outcome=MutationOutcomeKind.NOT_MUTABLE,
            descriptor=descriptor,
            tests_run=tests,
            reason=_why_broken(failed),
        )
    if breadth.too_broad(len(failed), len(tests)):
        return MutationAttempt(
            defect_id=defect.id,
            outcome=MutationOutcomeKind.NOT_MUTABLE,
            descriptor=descriptor,
            tests_run=tests,
            reason=breadth.reason(len(failed), len(tests)),
        )
    if killing:
        return MutationAttempt(
            defect_id=defect.id,
            outcome=MutationOutcomeKind.KILLED,
            descriptor=descriptor,
            tests_run=tests,
            killing_tests=killing,
        )

    unobserved = [outcome for outcome in result.outcomes if not outcome.completed]
    if unobserved:
        return MutationAttempt(
            defect_id=defect.id,
            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
            descriptor=descriptor,
            tests_run=tests,
            reason=_why_unobserved(unobserved, result.outcomes),
        )

    return MutationAttempt(
        defect_id=defect.id,
        outcome=MutationOutcomeKind.SURVIVED,
        descriptor=descriptor,
        tests_run=tests,
    )


def _why_broken(failed: list) -> str:
    names = sorted({outcome.error_type for outcome in failed})
    return (
        f"every one of the {len(failed)} tests that failed under the edit failed with "
        f"{' or '.join(names)}, which means the edited code no longer loads or names "
        "something that does not exist. Those failures say nothing about the named "
        "defect, so this is not counted as a kill and the defect goes to the static judge."
    )


def _why_unobserved(unobserved: list, outcomes: list) -> str:
    """Why a run that produced no red test also proved nothing.

    The two cases are worth separating, because only one of them says anything
    about the mutant. **Every** test failing to run is the signature of a mutant
    that broke the module rather than its behavior: a file that raises or fails
    to import dies during pytest's collection, before any test runs, so nothing
    is ever reported about any of them.

    That case is the reason this stage cannot simply read "no test went red" as
    a survival. Were it recorded as a kill instead — which it would be if
    collection errors reached the per-test reporting hook — an unloadable module
    would be credited as killed by every candidate test, inflating the criterion
    toward `strongly_supported` while nothing had actually been tested. Silent
    inflation is the failure #252 exists to remove.
    """
    if len(unobserved) == len(outcomes):
        return (
            f"none of the {len(outcomes)} candidate tests ran at all under the mutant, which is "
            "what a mutant that breaks the module rather than its behavior looks like: the file "
            "fails during collection and no test is reached. Nothing was learned about the "
            "tests, so this defect goes to the static judge."
        )
    names = ", ".join(outcome.test_id for outcome in unobserved[:5])
    more = "" if len(unobserved) <= 5 else f" and {len(unobserved) - 5} more"
    return (
        f"no test went red, but {len(unobserved)} of {len(outcomes)} did not complete under the "
        f"mutant ({names}{more}), so the tests cannot be called proven weak on this run"
    )


def _sources(regions: Sequence[Region], project_root: Path) -> dict[str, str]:
    """The text at head of every file the defect's regions name.

    A path that is not a file is omitted rather than raising, so that a change
    set naming a deleted file yields a `not_mutable` with a reason instead of an
    exception from a stage whose contract is to return.
    """
    sources: dict[str, str] = {}
    for region in regions:
        if region.path in sources:
            continue
        target = project_root / region.path
        if target.is_file():
            sources[region.path] = target.read_text(encoding="utf-8")
    return sources


def _not_mutable(defect: Defect, reason: str) -> MutationAttempt:
    return MutationAttempt(
        defect_id=defect.id, outcome=MutationOutcomeKind.NOT_MUTABLE, reason=reason
    )


def _not_attempted(defect: Defect, reason: str) -> MutationAttempt:
    return MutationAttempt(
        defect_id=defect.id, outcome=MutationOutcomeKind.NOT_ATTEMPTED, reason=reason
    )
