"""Deriving a criterion's evidence class from pair verdicts (#316).

The old chain asked a judge how strong a criterion's evidence was. This reduces
over verdicts already recorded, so every test here is about arithmetic and about
what the arithmetic refuses to claim — the unknown-defect cases are the point,
not an edge.
"""

from __future__ import annotations

import pytest

from acceptance.defects.support import derive_support, uncovered_defects
from acceptance.review_state import (
    Defect,
    DefectSet,
    ObligationType,
    PairVerdict,
    UnjudgedCause,
    UnjudgedPair,
)
from tests.support import make_obligation

_OBLIGATION = "daily-rate"


def _obligation(obligation_id: str = _OBLIGATION):
    return make_obligation(
        obligation_id, "The daily rate divides by the month's days.", ObligationType.FUNCTIONAL
    )


def _defect_set(count: int, obligation_id: str = _OBLIGATION) -> DefectSet:
    return DefectSet(
        obligation_id=obligation_id,
        defects=[
            Defect(
                id=f"{obligation_id}/d{index}",
                obligation_id=obligation_id,
                type="other",
                description=f"way {index} the change could fail it",
                code_refs=["billing.py#0"],
            )
            for index in range(1, count + 1)
        ],
    )


def _reasoned_empty(obligation_id: str = _OBLIGATION) -> DefectSet:
    return DefectSet(
        obligation_id=obligation_id,
        defects=[],
        reason="The criterion is true by construction; no change to it can fail.",
    )


def _verdict(defect_index: int, kills: bool, test_id: str = "test_billing.py::test_prorate"):
    return PairVerdict(defect_id=f"{_OBLIGATION}/d{defect_index}", test_id=test_id, kills=kills)


def _unjudged(defect_index: int, cause: UnjudgedCause, test_id: str = "test_billing.py::test_far"):
    return UnjudgedPair(
        defect_id=f"{_OBLIGATION}/d{defect_index}",
        test_id=test_id,
        cause=cause,
        reason="recorded rather than dropped",
    )


def _derive(defect_sets, verdicts, unjudged=(), obligations=None):
    return derive_support(
        obligations or [_obligation()],
        defect_sets,
        verdicts,
        list(unjudged),
    )[0]


# --- the fully-judged cases: the §9.3 bright lines, unchanged --------------


@pytest.mark.parametrize(
    "kills, expected, covered",
    [
        ([True, True], "strongly_supported", 2),
        ([True, False], "partially_supported", 1),
        ([False, False], "unsupported", 0),
    ],
)
def test_a_fully_judged_criterion_takes_the_class_its_kill_count_implies(kills, expected, covered):
    result = _derive(
        [_defect_set(len(kills))],
        [_verdict(index, kill) for index, kill in enumerate(kills, start=1)],
    )
    assert result.evidence_class == expected
    assert (result.covered, result.enumerated, result.unknown) == (covered, len(kills), 0)


def test_one_killing_test_covers_a_defect_however_many_others_survive_it():
    """Coverage is existential per defect, not a majority over its pairs.

    Three tests judged against one defect, one of which would fail on it: the
    defect is covered. Asserting this pins the reduction as *some test kills it*
    rather than *most tests kill it*, which is the difference between the §8.2
    question and a vote.
    """
    result = _derive(
        [_defect_set(1)],
        [
            _verdict(1, False, "test_billing.py::test_a"),
            _verdict(1, True, "test_billing.py::test_b"),
            _verdict(1, False, "test_billing.py::test_c"),
        ],
    )
    assert result.evidence_class == "strongly_supported"
    assert result.test_links == ["test_billing.py::test_b"]


# --- the unknown-defect cases: what the derivation refuses to claim --------


def test_an_unjudged_defect_stops_a_criterion_reaching_strongly_supported():
    """One killed, one never judged. `strongly` would be a claim an unknown
    could overturn; `partially` is true whatever the unjudged pair turns out to
    be, so that is what the evidence carries."""
    result = _derive(
        [_defect_set(2)], [_verdict(1, True)], unjudged=[_unjudged(2, UnjudgedCause.UNANSWERED)]
    )
    assert result.evidence_class == "partially_supported"
    assert (result.covered, result.enumerated, result.unknown) == (1, 2, 1)


def test_a_criterion_whose_only_evidence_is_unjudged_is_indeterminate_not_nominal():
    """With nothing known to be caught and something never judged, the honest
    answer is that the class cannot be decided. Reading it as `nominally` would
    report zero discriminating power that was never measured."""
    result = _derive(
        [_defect_set(2)], [_verdict(1, False)], unjudged=[_unjudged(2, UnjudgedCause.UNANSWERED)]
    )
    assert result.evidence_class == "indeterminate"
    assert (result.covered, result.enumerated, result.unknown) == (0, 2, 1)


def test_an_unjudged_defect_never_reads_as_a_surviving_one():
    """DR-164's trap, at this layer. A shed judgement and a verdict of *survives*
    must not produce the same class: two defects, one judged surviving and one
    never judged, is `indeterminate`, while two judged surviving is `unsupported`.
    """
    unjudged = _derive(
        [_defect_set(2)], [_verdict(1, False)], unjudged=[_unjudged(2, UnjudgedCause.UNANSWERED)]
    )
    both_judged = _derive([_defect_set(2)], [_verdict(1, False), _verdict(2, False)])
    assert unjudged.evidence_class != both_judged.evidence_class
    assert (unjudged.evidence_class, both_judged.evidence_class) == (
        "indeterminate",
        "unsupported",
    )


# --- the terminal and absent cases ----------------------------------------


def test_a_reasoned_empty_enumeration_gets_its_own_class_and_says_evidence_is_unobtainable():
    result = _derive([_reasoned_empty()], [])
    assert result.evidence_class == "no_plausible_defect"
    assert "not obtainable at this tier" in result.explanation
    assert result.enumerated == 0


@pytest.mark.parametrize("forbidden", ["strongly_supported", "unsupported"])
def test_a_reasoned_empty_enumeration_is_never_either_extreme(forbidden):
    """DR-312 resolved question 3 forbids both by name: `strongly_supported`
    would make looking least earn the strongest rating (#252), and `unsupported`
    would prescribe a test nobody can write."""
    assert _derive([_reasoned_empty()], []).evidence_class != forbidden


def test_a_criterion_no_test_would_fail_on_is_unsupported():
    """`unsupported` is the only answer this stage gives for "no test catches
    any of these".

    §9.3's `nominally_supported` — a relevant-looking test that catches nothing
    — is deliberately not produced: separating it from "no test goes near this"
    needs the judge to say which of two things it meant by *no*, and M8.4's
    defect injection cannot make that distinction even in principle.
    """
    assert _derive([_defect_set(2)], []).evidence_class == "unsupported"
    assert _derive([_defect_set(2)], [_verdict(1, False), _verdict(2, False)]).evidence_class == (
        "unsupported"
    )


def test_a_criterion_whose_pairs_were_offered_and_unanswered_is_indeterminate():
    """`unsupported` says no test bears on the criterion. A review that formed
    the pairs, asked, and got nothing back has not established that — it has
    established only that it failed to ask successfully, which is a fact about
    the review rather than about the repo."""
    result = _derive(
        [_defect_set(2)],
        [],
        unjudged=[_unjudged(1, UnjudgedCause.UNANSWERED), _unjudged(2, UnjudgedCause.UNANSWERED)],
    )
    assert result.evidence_class == "indeterminate"


def test_a_prefilter_exclusion_counts_as_a_surviving_pair_not_an_unknown_one():
    """The prefilter excludes only what it can PROVE unreachable, so an
    exclusion is a *survives* established statically rather than a judgement
    nobody made. Reading it as unknown would make a filter doing its job
    indistinguishable from a judge shedding work — the two failures
    `UnjudgedCause` exists to keep apart, whose remedies are opposite.
    """
    result = _derive(
        [_defect_set(2)],
        [_verdict(1, True)],
        unjudged=[_unjudged(2, UnjudgedCause.PREFILTERED)],
    )
    assert result.evidence_class == "partially_supported"
    assert result.unknown == 0

    # The control: the same shape with the other cause cannot reach a verdict.
    shed = _derive(
        [_defect_set(2)],
        [_verdict(1, True)],
        unjudged=[_unjudged(2, UnjudgedCause.UNANSWERED)],
    )
    assert shed.unknown == 1


def test_a_criterion_nothing_enumerated_for_is_indeterminate():
    """Distinct from the reasoned-empty case: no `DefectSet` at all means the
    enumeration never considered it, which is an absent judgement rather than
    one standing behind an empty result."""
    assert _derive([], []).evidence_class == "indeterminate"


# --- the derived test → defect → obligation edge ---------------------------


def test_test_links_carry_only_the_tests_judged_to_fail_on_a_defect():
    """The edge that replaces the retired mapping stage. A test judged against
    the criterion's defects and found to fail on none of them is not evidence
    for it, so it must not appear as a link."""
    result = _derive(
        [_defect_set(2)],
        [
            _verdict(1, True, "test_billing.py::test_kills"),
            _verdict(2, False, "test_billing.py::test_survives"),
        ],
    )
    assert result.test_links == ["test_billing.py::test_kills"]


# --- what becomes a recommendation ----------------------------------------


def test_a_defect_some_test_kills_produces_no_recommendation_input():
    """#250 and #287 made structural. A covered defect never reaches the
    recommendation stage, so a prescription for evidence the review already
    holds cannot be composed in the first place."""
    assert uncovered_defects([_defect_set(2)], [_verdict(1, True), _verdict(2, False)]) == [
        (_OBLIGATION, f"{_OBLIGATION}/d2")
    ]


def test_an_unjudged_defect_is_offered_for_recommendation():
    """The conservative error, chosen deliberately. Silence about a defect
    nobody judged is the invisible gap #312 exists to remove; a prescription
    that may be redundant is visible and correctable."""
    assert uncovered_defects([_defect_set(1)], []) == [(_OBLIGATION, f"{_OBLIGATION}/d1")]


def test_a_reasoned_empty_enumeration_offers_nothing_to_recommend():
    assert uncovered_defects([_reasoned_empty()], []) == []


# --- determinism -----------------------------------------------------------


def test_the_derivation_makes_no_model_call_and_repeats_exactly():
    """No client is passed at all, which is the strongest form of this
    assertion: the signature makes a call impossible rather than the test
    observing that none happened."""
    args = ([_defect_set(3)], [_verdict(1, True), _verdict(2, False), _verdict(3, True)])
    first = derive_support([_obligation()], *args, [])
    second = derive_support([_obligation()], *args, [])
    assert [r.model_dump() for r in first] == [r.model_dump() for r in second]
