"""Which defect types the enumerator is walked through, per obligation type.

The contents are `docs/DR-313-defect-taxonomy.md`; the reasoning for the shape
is DR-312's resolved question 4. Two things about it are load-bearing and easy
to undo by accident:

**The list is short on purpose.** Six entries per obligation plus the `other`
escape. A checklist earns its keep by driving recall, and a twenty-item list
walked for every obligation dilutes the prompt and invites odd defects being
forced into the nearest slot — the failure mode DR-312 names.

**Two obligation types get no checklist, and that is not the same as an empty
one.** `HUMAN_REVIEW` exists because a machine cannot settle the question, and
`TEST_DEMAND` because DR-313 decision 2 excludes it: the enumerator may never
see the tests (the #252 mitigation), and a `test_demand` obligation is *about*
a test. `enumerable` is the predicate; an obligation it rejects gets no defect
set at all, which downstream must keep distinct from an empty set.
"""

from __future__ import annotations

from acceptance.review_state import DefectType, ObligationType

__all__ = ["CHECKLIST", "CORE", "DESCRIPTIONS", "checklist_for", "enumerable"]

# Walked for every enumerable obligation type, whatever it is.
CORE: tuple[DefectType, ...] = (
    DefectType.QUALIFIER_IGNORED,
    DefectType.CONDITION_INVERTED,
    DefectType.SCOPE_TOO_NARROW,
    DefectType.NOT_WIRED,
)

# Added to CORE for the obligation type that names them. An obligation type
# absent from this mapping is one `enumerable` rejects.
_BY_TYPE: dict[ObligationType, tuple[DefectType, ...]] = {
    ObligationType.FUNCTIONAL: (
        DefectType.WRONG_OUTPUT_SHAPE,
        DefectType.MISSING_CASE,
    ),
    ObligationType.BOUNDARY: (
        DefectType.BOUNDARY_WRONG_SIDE,
        DefectType.BOUNDARY_UNHANDLED,
    ),
    ObligationType.ERROR_HANDLING: (
        DefectType.ERROR_SWALLOWED,
        DefectType.WRONG_ERROR_SURFACED,
    ),
    ObligationType.INVARIANT: (
        DefectType.ESTABLISHED_NOT_MAINTAINED,
        DefectType.UNENFORCED_ON_ONE_PATH,
    ),
    ObligationType.REGRESSION: (
        DefectType.PRIOR_BEHAVIOR_ALTERED,
        DefectType.PRIOR_BEHAVIOR_REMOVED,
    ),
    ObligationType.COMPATIBILITY: (
        DefectType.OLD_INPUT_REJECTED,
        DefectType.STORED_FORM_UNREADABLE,
    ),
    ObligationType.EXPLANATION_OBSERVABILITY: (
        DefectType.EXPLANATION_ABSENT,
        DefectType.EXPLANATION_STATES_WRONG_CAUSE,
    ),
    ObligationType.DOCS_CONFIG: (
        DefectType.DOCUMENTED_NOT_IMPLEMENTED,
        DefectType.DEFAULT_DISAGREES_WITH_DOCS,
    ),
}

# What each type means, rendered into the enumerator's prompt. A checklist of
# bare slugs is a list of words to pattern-match; a checklist of sentences is
# something to walk. `OTHER` is described where the prompt introduces it, since
# what it means is "none of the above" rather than a failure of its own.
DESCRIPTIONS: dict[DefectType, str] = {
    DefectType.QUALIFIER_IGNORED: (
        "the behaviour is implemented but a qualifier the obligation states — "
        "only, at most, when X, except Y — is not honoured"
    ),
    DefectType.CONDITION_INVERTED: "a guard or comparison runs the wrong way round",
    DefectType.SCOPE_TOO_NARROW: (
        "the behaviour holds for some of the inputs the obligation covers but not all of them"
    ),
    DefectType.NOT_WIRED: (
        "the logic exists and is correct, but nothing on the delivered path calls it"
    ),
    DefectType.WRONG_OUTPUT_SHAPE: (
        "the right value is produced in the wrong form — type, units, ordering, nesting"
    ),
    DefectType.MISSING_CASE: "an input the obligation covers falls through unhandled",
    DefectType.BOUNDARY_WRONG_SIDE: (
        "the boundary is off by one, or inclusive where it should be exclusive"
    ),
    DefectType.BOUNDARY_UNHANDLED: "the extreme value itself is not handled at all",
    DefectType.ERROR_SWALLOWED: "the failure is caught and discarded, so the caller cannot see it",
    DefectType.WRONG_ERROR_SURFACED: (
        "a failure is reported, but as the wrong kind, or naming the wrong cause"
    ),
    DefectType.ESTABLISHED_NOT_MAINTAINED: (
        "the invariant holds when first set up but is not preserved by later operations"
    ),
    DefectType.UNENFORCED_ON_ONE_PATH: (
        "the invariant is enforced on one route into the code and not on another"
    ),
    DefectType.PRIOR_BEHAVIOR_ALTERED: "behaviour that was meant to stay the same has changed",
    DefectType.PRIOR_BEHAVIOR_REMOVED: "behaviour that was meant to stay is gone entirely",
    DefectType.OLD_INPUT_REJECTED: "input the previous version accepted is now refused",
    DefectType.STORED_FORM_UNREADABLE: "data written by the previous version can no longer be read",
    DefectType.EXPLANATION_ABSENT: "the situation arises but nothing is said about it",
    DefectType.EXPLANATION_STATES_WRONG_CAUSE: (
        "something is said, but it names a cause that is not the real one"
    ),
    DefectType.DOCUMENTED_NOT_IMPLEMENTED: (
        "the documented behaviour and the delivered behaviour disagree"
    ),
    DefectType.DEFAULT_DISAGREES_WITH_DOCS: (
        "the configured default differs from the one that is written down"
    ),
}

CHECKLIST: dict[ObligationType, tuple[DefectType, ...]] = {
    obligation_type: CORE + extra for obligation_type, extra in _BY_TYPE.items()
}


def enumerable(obligation_type: ObligationType) -> bool:
    """Whether defects are enumerated for an obligation of this type at all.

    False for `TEST_DEMAND` and `HUMAN_REVIEW` (DR-313 decision 2). The caller
    must record *no set* for these rather than an empty one: an empty set means
    "looked, found no plausible static defect, here is why", and claiming that
    about an obligation the stage never examined would be a false negative
    wearing a reason.
    """
    return obligation_type in CHECKLIST


def checklist_for(obligation_type: ObligationType) -> tuple[DefectType, ...]:
    """The defect types walked for this obligation type, core entries first.

    Empty for a type `enumerable` rejects, so a caller that skips the predicate
    gets an empty checklist rather than a silently core-only one.
    """
    return CHECKLIST.get(obligation_type, ())
