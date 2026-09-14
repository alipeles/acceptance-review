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

from collections.abc import Callable, Sequence
from pathlib import Path

from acceptance.execution.outcome import SandboxRunResult, TestOutcomeKind
from acceptance.execution.sandbox import SandboxConfig, run_tests
from acceptance.mutation.attempt import (
    MutationAttempt,
    MutationDescriptor,
    MutationOutcomeKind,
)
from acceptance.mutation.baseline import Baseline
from acceptance.mutation.injection import mutated_copy
from acceptance.mutation.region import Region, regions_for
from acceptance.mutation.validity import DEFAULT_MAX_EDIT_LINES, invalidity_reason
from acceptance.review_state import ChangeSet, Defect, DefectSet

__all__ = ["DescriptorBuilder", "run_mutations"]

#: Given one defect, the regions it named, and the text of each of those files
#: at head, produce the smallest edit that makes the defect true — or `None`
#: when it cannot be expressed as one contiguous span replacement.
DescriptorBuilder = Callable[[Defect, Sequence[Region], dict[str, str]], MutationDescriptor | None]


def run_mutations(
    defect_sets: Sequence[DefectSet],
    change_set: ChangeSet,
    project_root: Path,
    baseline: Baseline,
    build_descriptor: DescriptorBuilder,
    config: SandboxConfig | None = None,
    max_edit_lines: int = DEFAULT_MAX_EDIT_LINES,
) -> list[MutationAttempt]:
    """One attempt per defect, in the order the defect sets hold them.

    Returns an attempt for every defect, including the ones nothing could be
    done with. A defect missing from this list would be indistinguishable from
    one that survived, which is the failure `MutationAttempt`'s validators exist
    to prevent.
    """
    defects = [defect for defect_set in defect_sets for defect in defect_set.defects]

    if baseline.halted:
        return [
            _not_attempted(defect, f"the review halted before injection: {baseline.halt_reason}")
            for defect in defects
        ]
    if not baseline.usable_tests:
        return [
            _not_attempted(
                defect,
                "no candidate test survived the control run, so there is nothing a mutant "
                "could be observed against",
            )
            for defect in defects
        ]

    return [
        _attempt(
            defect,
            change_set,
            project_root,
            baseline.usable_tests,
            build_descriptor,
            config,
            max_edit_lines,
        )
        for defect in defects
    ]


def _attempt(
    defect: Defect,
    change_set: ChangeSet,
    project_root: Path,
    tests: list[str],
    build_descriptor: DescriptorBuilder,
    config: SandboxConfig | None,
    max_edit_lines: int,
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

    return _classify(defect, descriptor, tests, result)


def _classify(
    defect: Defect,
    descriptor: MutationDescriptor,
    tests: list[str],
    result: SandboxRunResult,
) -> MutationAttempt:
    """Read the mutated run as killed, survived, or nothing at all.

    A kill needs one red test. A *survival* needs every requested test to have
    completed, and that asymmetry is deliberate: a survival is the finding that
    the builder's tests are proven weak, so it may not rest on tests nobody
    watched. A partly-observed run that produced no red test is recorded as
    `not_attempted` and handed to the static judge, which is the weaker claim
    and the honest one.
    """
    killing = [
        outcome.test_id for outcome in result.outcomes if outcome.kind is TestOutcomeKind.FAILED
    ]
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
        names = ", ".join(outcome.test_id for outcome in unobserved[:5])
        more = "" if len(unobserved) <= 5 else f" and {len(unobserved) - 5} more"
        return MutationAttempt(
            defect_id=defect.id,
            outcome=MutationOutcomeKind.NOT_ATTEMPTED,
            descriptor=descriptor,
            tests_run=tests,
            reason=(
                f"no test went red, but {len(unobserved)} of {len(result.outcomes)} did not "
                f"complete under the mutant ({names}{more}), so the tests cannot be called "
                "proven weak on this run"
            ),
        )

    return MutationAttempt(
        defect_id=defect.id,
        outcome=MutationOutcomeKind.SURVIVED,
        descriptor=descriptor,
        tests_run=tests,
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
