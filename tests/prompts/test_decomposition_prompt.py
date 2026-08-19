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
from acceptance.review_state import Disposition, ObligationType, RequiredEvidence
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
    """The typed field, not a substring of the description.

    This started as `"test" in description.lower()` — a heuristic over free
    text, which is the shape this project's markdown-never-as-interchange
    invariant exists to forbid, and it could not tell "a test asserts X" from a
    behavior obligation that merely mentions testing. DR-232 added the type so
    the question has an answer that does not require reading English.
    """
    return obligation.type is ObligationType.TEST_DEMAND


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
def test_every_scope_exclusion_yields_an_obligation_satisfied_by_absence(derived, requirement_id):
    """#153. #230 split five siblings three ways in one call; #219 recorded the
    opposite half. #235 made the rule uniform by declining them all, which was
    stable but left nothing downstream to check that the boundary was respected.

    So they yield again — and the thing that makes that safe, rather than a
    return to #230, is that the obligation is marked as satisfied by an ABSENCE
    rather than being an ordinary obligation nobody wrote a test for.

    This asserts `satisfied_by_absence`, not which evidence is required (#266).
    The two were one field until a scope exclusion naming a BEHAVIOR turned out
    to want a regression test. What the heading settles beyond argument is that
    the obligation is met by work not done; whether a test is owed for it is a
    judgement, and the test below is the one that covers it.
    """
    disposition = _disposition(derived, requirement_id)
    assert disposition.disposition is Disposition.YIELDED

    obligations = _obligations_of(derived, requirement_id)
    assert obligations, f"{requirement_id} yielded no obligation"
    for obligation in obligations:
        assert obligation.satisfied_by_absence, (
            f"{obligation.id} is not marked as satisfied by an absence"
        )


def test_only_exclusions_are_satisfied_by_absence(derived):
    """The negative case, and the reason the test above cannot stand alone: it
    asserts exclusions ARE marked, which an implementation marking EVERY
    obligation would satisfy — and that implementation would silently exempt the
    whole mandate.

    Raised by the tool's own recommendation on #153's Gate 2, which asked for
    "assert the ordinary non-exclusion requirement is not marked CODE_ONLY".
    """
    exclusion_obligation_ids = {
        obligation.id for i in _EXCLUSION_IDS for obligation in _obligations_of(derived, i)
    }
    misfiled = [
        obligation.id
        for obligation in derived.obligations
        if obligation.id not in exclusion_obligation_ids and obligation.satisfied_by_absence
    ]

    assert not misfiled, f"non-exclusion obligations marked satisfied-by-absence: {misfiled}"


def test_the_ordinary_requirements_still_require_test_evidence(derived):
    """The false-green guard on #266's central risk.

    Which evidence an obligation requires is now a MODEL judgement, where the
    scope-exclusion heading used to settle it structurally. That buys the
    flexibility a behavioural exclusion needs, and it costs the guarantee: a
    model answering `code_only` too freely would excuse the mandate from test
    evidence one obligation at a time, and every later stage would honour it
    without complaint. Nothing downstream can catch that — an obligation off the
    test axis produces no finding, by design.

    So it is caught here, against real responses. The three Constraints in the
    task file are ordinary behavioural requirements about CSV output; if any of
    them comes back excused from test evidence, the judgement is too loose.
    """
    ordinary = [
        obligation
        for requirement_id in ("constraint-01", "constraint-02", "constraint-03")
        for obligation in _obligations_of(derived, requirement_id)
    ]
    assert ordinary, "the ordinary constraints yielded no obligations"

    excused = [o.id for o in ordinary if not o.required_evidence.requires_tests]
    assert not excused, f"ordinary behavioural requirements excused from test evidence: {excused}"


def test_a_narrowed_requirement_says_why(derived):
    """A narrowing with no reason is indistinguishable from the question being
    skipped, and `obligations.py` discards one — so any obligation that survives
    with less than both kinds required must carry the sentence that justifies
    it. Asserted over whatever this corpus happens to narrow, including nothing:
    the property is about the pairing, not about any particular obligation."""
    unreasoned = [
        o.id
        for o in derived.obligations
        if o.required_evidence is not RequiredEvidence.CODE_AND_TESTS
        and not o.required_evidence_reason.strip()
    ]

    assert not unreasoned, f"evidence narrowed with no reason given: {unreasoned}"


def test_sibling_exclusions_share_one_disposition(derived):
    """#230's own property, and distinct from the parametrized test above.

    "Each of these is declined" and "these are all disposed of the SAME way"
    are different assertions. The first pins a value and says nothing about
    consistency; the second is what the requirement states, and it is the one
    that fails on the three-declined/two-inverted split #230 was filed for.

    Asserting equality rather than a fixed value on purpose: if the uniform
    disposition ever changes, this test should still be measuring consistency
    rather than needing to be rewritten to a new constant.
    """
    kinds = {_disposition(derived, i).disposition for i in _EXCLUSION_IDS}

    assert len(kinds) == 1, (
        "siblings under one Scope exclusions heading were split: "
        f"{ {i: _disposition(derived, i).disposition for i in _EXCLUSION_IDS} }"
    )


def test_sibling_exclusions_differing_in_content_still_share_a_disposition(derived):
    """The boundary the recommendation names: the four bullets name four
    different excluded topics — currencies, pagination, scheduling,
    compression — so passing the test above cannot be an artifact of them
    saying the same thing. Consistency of disposition, not of content."""
    subjects = {
        obligation.description for i in _EXCLUSION_IDS for obligation in _obligations_of(derived, i)
    }

    assert len(subjects) == len(_EXCLUSION_IDS), (
        f"the four exclusions should name four different excluded topics; got {sorted(subjects)}"
    )


@pytest.mark.parametrize("requirement_id", _EXCLUSION_IDS)
def test_an_exclusion_obligation_states_no_property_to_preserve(derived, requirement_id):
    """The #219 defect, moved to where it can now recur. #219 was the positive
    reframing performed in the `reason` field of a declined exclusion; with the
    exclusion yielding again (#153), the same reframing has a better place to
    hide — the obligation's own text.

    "The change does not alter how the invoice list is paginated" is the form
    that is wanted. "Keep the existing pagination" is #219 verbatim, and would
    now be a real obligation rather than dead free text.
    """
    for obligation in _obligations_of(derived, requirement_id):
        text = f"{obligation.description} {obligation.observable_behavior}".lower()
        offending = [word for word in _PRESERVATION_WORDS if word in text]
        assert not offending, (
            f"{obligation.id} states a property to preserve: {obligation.description!r}"
        )


def test_no_obligation_anywhere_demands_the_excluded_work(derived):
    """The inversion, and the sharpest form of #230. Four of six exclusions in
    this bundle's Gate 1 derived obligations to DO the excluded work —
    "Whether obligation identifiers are stable across task-file edits, which is
    #231" became "Keep obligation identifiers stable across task-file edits".

    Checked across the WHOLE obligation set, not just the exclusion
    dispositions, because #210 shows an exclusion's content can surface under a
    neighbouring requirement's obligation instead of its own.

    #153 sharpened this rather than relaxing it. While exclusions were declined
    outright, "no obligation anywhere names the excluded subject" was a sound
    proxy for the inversion. It no longer is: an exclusion's own obligation must
    name its subject to say the change stayed away from it. So the two halves
    are now asserted separately —

      * the exclusion's OWN obligation may name the subject, but only in the
        absence form; and
      * NO OTHER obligation may name it at all, which is the #210 leak.

    Dropping to only the second half would let "Support these currencies" pass
    as long as it landed under `exclusion-01`, which is the original defect.
    """
    own_ids = {obligation.id for i in _EXCLUSION_IDS for obligation in _obligations_of(derived, i)}

    leaked = [
        (obligation.id, obligation.description)
        for obligation in derived.obligations
        if obligation.id not in own_ids
        for subject in _EXCLUDED_SUBJECTS
        if subject in f"{obligation.description} {obligation.observable_behavior}".lower()
    ]
    assert not leaked, f"excluded work surfaced under another requirement: {leaked}"

    not_absence = [
        (obligation.id, obligation.description)
        for i in _EXCLUSION_IDS
        for obligation in _obligations_of(derived, i)
        if "does not" not in obligation.description.lower()
    ]
    assert not not_absence, f"an exclusion obligation is not in the absence form: {not_absence}"
