"""Prompt-quality tests for obligation derivation (#232, #219, #230), over REAL
responses.

`tests/requirement/test_requirement_map.py` injects hand-authored responses, so
it verifies the plumbing and cannot fail when the derivation prompt is edited.
These replay a committed corpus instead, so the assertions are about what the
model actually derives. Re-record with:

    ACCEPTANCE_RECORD=1 pytest tests/prompts/test_decomposition_prompt.py -q

The task file is about exporting invoices, deliberately, and shares that domain
with `test_linking_prompt.py`. A transcript embeds its whole request, so
recording against this repo's own task files would commit its diffs into
fixtures — and #204 measured that a control file on unrelated subject matter
reproduces these defects exactly, which is what rules out dogfood contamination
as the cause.
"""

from __future__ import annotations

import pytest

from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import Disposition
from tests.support import recorded_client

# Both properties in one file, so one recording covers them.
#
#   * Three Completion expectations of ONE shape ("A test asserts that ..."),
#     each restating a Constraint almost word for word. #232: the framing was
#     dropped and the obligation collapsed into its Constraint twin. Three of
#     them, because the measured failure was 2 kept / 3 dropped IN ONE CALL —
#     one example cannot distinguish "kept" from "kept this time".
#   * Four sibling Scope exclusions, three citing an issue. #230: these derived
#     obligations to DO the excluded work — "Which currencies the amount column
#     supports, which is #401" is a trap, because its inverted form ("support
#     these currencies") is a plausible-sounding requirement.
_TASK = """# Task
Export invoices to a CSV file.

## Constraints
- The export writes a header row naming every column.
- The export escapes embedded commas in the customer name.
- The amount column is written with exactly two decimal places.

## Scope exclusions
- Which currencies the amount column supports, which is #401.
- How the invoice list is paginated, which is #402.
- Whether the export runs on a schedule, which is #403.
- Compressing the output file.

## Completion expectations
- A test asserts that the export writes a header row naming every column.
- A test asserts that an embedded comma in the customer name is escaped.
- A test asserts that the amount column has exactly two decimal places.
"""

_EXCLUSION_IDS = ["exclusion-01", "exclusion-02", "exclusion-03", "exclusion-04"]
_TEST_DEMAND_IDS = ["completion-01", "completion-02", "completion-03"]

# The subject each exclusion names. An obligation mentioning one of these is
# the inversion: the excluded work asserted as a requirement of this change.
_EXCLUDED_SUBJECTS = ["currenc", "paginat", "schedul", "compress"]

# A reason that says the change must hold something is an obligation written
# into a free-text field. "unchanged" and "preserve" are how it actually
# surfaced (#230: "Preserve the scope exclusion that ...").
_PRESERVATION_WORDS = ["preserve", "keep ", "maintain", "unchanged", "must "]


@pytest.fixture(scope="module")
def derived():
    return decompose(parse_task_file(_TASK), recorded_client())


def _disposition(decomposition, requirement_id: str):
    found = decomposition.requirement_map.disposition_for(requirement_id)
    assert found is not None, f"{requirement_id} has no disposition"
    return found


def _obligations_of(decomposition, requirement_id: str):
    by_id = {obligation.id: obligation for obligation in decomposition.obligations}
    return [by_id[i] for i in _disposition(decomposition, requirement_id).obligation_ids]


def _demands_a_test(obligation) -> bool:
    return "test" in f"{obligation.description} {obligation.observable_behavior}".lower()


# --- #232: a requirement for a test is a requirement for a test ---------------


@pytest.mark.parametrize("requirement_id", _TEST_DEMAND_IDS)
def test_a_criterion_demanding_a_test_yields_an_obligation_demanding_a_test(
    derived, requirement_id
):
    """The headline judgement. "A test asserts that X" must not derive into X.

    Asserting on the derived obligation's own text, NOT on whether it stayed
    separate from its Constraint twin. Gate 1 run 2 of this bundle produced the
    separation for the wrong reason — an 8-obligation transitive clique was
    contradicted, so #144's clique rule merged nothing in it — and a
    non-merger assertion passed while every obligation had lost its framing.
    That test would keep passing with this fix reverted.
    """
    obligations = _obligations_of(derived, requirement_id)

    assert obligations, f"{requirement_id} yielded nothing"
    assert any(_demands_a_test(o) for o in obligations), (
        f"{requirement_id} lost its test framing: {[o.description for o in obligations]}"
    )


def test_every_criterion_of_the_same_shape_is_treated_the_same_way(derived):
    """#232 as filed says the framing is unstable ACROSS task files. Measured on
    this bundle's own Gate 1 run 4, it is unstable WITHIN one call over one
    section: two of five kept the framing and three dropped it, and the three
    that dropped it then merged with their Constraint twin.

    So "usually kept" is not the property. Three identically-shaped bullets get
    three identical treatments, or the derivation is drawing a distinction the
    task file does not make.
    """
    kept = {
        requirement_id
        for requirement_id in _TEST_DEMAND_IDS
        if any(_demands_a_test(o) for o in _obligations_of(derived, requirement_id))
    }

    assert kept == set(_TEST_DEMAND_IDS), (
        f"same sentence shape, different treatment: kept for {sorted(kept)}, "
        f"dropped for {sorted(set(_TEST_DEMAND_IDS) - kept)}"
    )


@pytest.mark.parametrize("requirement_id", ["constraint-01", "constraint-02", "constraint-03"])
def test_a_constraint_stating_a_behaviour_is_not_given_test_framing(derived, requirement_id):
    """The converse, and it is not hypothetical: the first cut of the #232 fix
    caused it. Told emphatically to keep the framing on every requirement of
    that shape, derivation began SUPPLYING it — this repo's `constraint-05`,
    which says nothing about a test, derived as "A test asserts that ...".

    That is the same loss in the other direction. Once the Constraint and the
    Completion expectation both read "a test asserts X" they are one statement,
    linking merges them correctly, and the demand for the test disappears
    exactly as it did before the fix.
    """
    framed = [o.description for o in _obligations_of(derived, requirement_id) if _demands_a_test(o)]

    assert not framed, f"{requirement_id} demands no test; framing was invented: {framed}"


# --- #219 / #230: scope exclusions ------------------------------------------


@pytest.mark.parametrize("requirement_id", _EXCLUSION_IDS)
def test_every_scope_exclusion_is_declined(derived, requirement_id):
    """#230: five siblings under one heading were split three ways in one call,
    and #219 recorded the opposite half — declined despite the prompt then
    forbidding it. Neither is a stable rule, so the rule is now uniform: a
    scope exclusion names work the change must not do, and yields nothing.
    """
    assert _disposition(derived, requirement_id).disposition is Disposition.NO_OBLIGATION


@pytest.mark.parametrize("requirement_id", _EXCLUSION_IDS)
def test_a_declined_exclusion_states_no_property_to_preserve(derived, requirement_id):
    """The #219 defect exactly: declining, and then performing the positive
    reframing in the reason field anyway — "it preserves the existing strength
    classifier unchanged" IS the obligation, written where nothing downstream
    can act on it."""
    reason = (_disposition(derived, requirement_id).reason or "").lower()

    assert reason.strip(), f"{requirement_id} declined without a reason"
    offending = [word for word in _PRESERVATION_WORDS if word in reason]
    assert not offending, f"{requirement_id} states a property to preserve: {reason!r}"


def test_no_obligation_anywhere_demands_the_excluded_work(derived):
    """The inversion, and the sharpest form of #230. Four of six exclusions in
    this bundle's Gate 1 derived obligations to DO the excluded work —
    "Whether obligation identifiers are stable across task-file edits, which is
    #231" became "Keep obligation identifiers stable across task-file edits".

    Checked across the WHOLE obligation set, not just the exclusion
    dispositions, because #210 shows an exclusion's content can surface under a
    neighbouring requirement's obligation instead of its own.
    """
    inverted = [
        (obligation.id, obligation.description)
        for obligation in derived.obligations
        for subject in _EXCLUDED_SUBJECTS
        if subject in f"{obligation.description} {obligation.observable_behavior}".lower()
    ]

    assert not inverted, f"excluded work asserted as an obligation: {inverted}"
