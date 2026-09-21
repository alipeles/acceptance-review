"""Turns what execution observed into the record the rating already reads.

DR-171 Decision 7, and the reason the mutation stage needs no rating logic of
its own: a `PairVerdict` carrying `DEFECT_KILLED` says the same thing as one
carrying `STATIC`, only better known. `defects/support.py` reduces both with the
same arithmetic, so there is one implementation of the rating rather than two
that can drift.

This module also answers the question that makes the whole tier worth building:
**what is left for the static judge?** Everything execution settled is removed
from the defect sets on their way to `judge_pairs`, so the expensive stage sees
only the defects injection could not reach. Under the original decision the
static judge ran first and execution corrected it afterwards, which paid for
both.

A verdict is emitted for every test the mutant was run against, not only the
ones that went red. A pair nobody recorded is indistinguishable from one judged
*survives*, which is the same reason `UnjudgedPair` exists on the static side.
"""

from __future__ import annotations

from collections.abc import Sequence

from acceptance.defects.pair_mapping import defect_text
from acceptance.evidence_tier import EvidenceTier
from acceptance.mutation.attempt import MutationAttempt, MutationOutcomeKind
from acceptance.review_state import DefectSet, PairVerdict

__all__ = ["pairs_not_worth_asking", "remaining_defect_sets", "verdicts_from"]


def pairs_not_worth_asking(
    attempts: Sequence[MutationAttempt],
) -> dict[tuple[str, str], str]:
    """Pairs the run already answered well enough to spend the model call elsewhere.

    The second, weaker use of the injection run (#340). `verdicts_from` above is
    the strong use and is unchanged: it needs a **verified** edit, because a
    verdict is evidence. This needs only an **observed** one, because the answer
    it produces is not a verdict at all — it decides which questions are worth
    asking, and a pair it removes is recorded as unjudged and rated as unknown.

    Returned for an attempt where some candidate test **failed** under the edit:
    that edit demonstrably changed what the code does, so a test that went on
    passing under it is not sensitive to the change. The tests that failed are
    **not** included — a test going red does not on its own say the named defect
    is what it caught, so they are still asked about.

    Nothing is returned for a `survived` attempt. An edit nothing failed under
    cannot be told apart from an edit that changed nothing, so it has shown
    nothing and must skip nothing.

    Nothing is returned for a **settled** attempt either. Its defect leaves
    through `remaining_defect_sets` and `verdicts_from` gives every one of its
    pairs a real verdict, so listing them here would record a pair as both
    judged and skipped.

    The value is the sentence the report shows, naming the attempt the decision
    rests on — `UnjudgedPair` carries a reason and this is the only place that
    knows what was injected.
    """
    skipped: dict[tuple[str, str], str] = {}
    for attempt in attempts:
        if attempt.settled or attempt.outcome is not MutationOutcomeKind.KILLED:
            continue
        killing = set(attempt.killing_tests)
        if not killing:
            continue
        for test_id in attempt.tests_run:
            if test_id in killing:
                continue
            skipped[(attempt.defect_id, test_id)] = (
                "not asked: the test still passed when this defect was injected, "
                f"and {len(killing)} other candidate test(s) failed under the same "
                "edit. The edit was not verified, so this is not evidence that the "
                "test fails to catch the defect."
            )
    return skipped


def verdicts_from(
    attempts: Sequence[MutationAttempt],
    defect_sets: Sequence[DefectSet],
) -> list[PairVerdict]:
    """One verdict per (settled defect, test the mutant ran against).

    `carry_key` is deliberately left empty, so a later run never carries an
    executed verdict forward. Carrying one would assert that a defect the code
    has since moved under is still killed by the same test, on the strength of a
    run that no longer describes the code. The static side carries because a
    re-judgement costs a model call; re-running costs CPU time and zero tokens,
    which is the cheaper thing to spend.
    """
    texts = {
        defect.id: defect_text(defect)
        for defect_set in defect_sets
        for defect in defect_set.defects
    }

    verdicts: list[PairVerdict] = []
    for attempt in attempts:
        # Settled, not merely observed: an unverified edit may not have made
        # the defect true, so its test results say nothing about the defect.
        if not attempt.settled:
            continue
        killing = set(attempt.killing_tests)
        for test_id in attempt.tests_run:
            verdicts.append(
                PairVerdict(
                    defect_id=attempt.defect_id,
                    test_id=test_id,
                    kills=test_id in killing,
                    reason=_reason(attempt, kills=test_id in killing),
                    tier=EvidenceTier.DEFECT_KILLED,
                    defect_text=texts.get(attempt.defect_id, ""),
                )
            )
    return verdicts


def remaining_defect_sets(
    attempts: Sequence[MutationAttempt],
    defect_sets: Sequence[DefectSet],
) -> list[DefectSet]:
    """`defect_sets` with every defect execution settled removed.

    This is what the static pair judgement is given. A set left with no defects
    is dropped entirely rather than passed on empty: `DefectSet` requires a
    reason on an empty set, and one written here would claim the enumeration
    found nothing plausible when in fact execution answered all of it.

    The *full* sets still go to `derive_support`, so the denominator a criterion
    is rated against is unchanged. Only the question put to the model shrinks.
    """
    settled = {attempt.defect_id for attempt in attempts if attempt.settled}
    if not settled:
        return list(defect_sets)

    remaining: list[DefectSet] = []
    for defect_set in defect_sets:
        keep = [defect for defect in defect_set.defects if defect.id not in settled]
        if not keep:
            continue
        if len(keep) == len(defect_set.defects):
            remaining.append(defect_set)
            continue
        remaining.append(defect_set.model_copy(update={"defects": keep}))
    return remaining


def _reason(attempt: MutationAttempt, *, kills: bool) -> str:
    """Short, and says that this was observed rather than predicted.

    Kept short on purpose: DR-312 decision 3 holds a pair verdict's reason to a
    sentence, because the caching discount is input-only and output growth never
    amortizes.
    """
    if kills:
        return "The test failed when the defect was injected."
    if attempt.outcome is MutationOutcomeKind.KILLED:
        return "The test still passed when the defect was injected; another test caught it."
    return "The test still passed when the defect was injected."
