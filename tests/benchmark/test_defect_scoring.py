"""#315: defect-set ground truth, and scoring a review's recorded defects.

The whole point of this module is that two failures stay apart — the enumerator
missed the defect, and the judge missed the kill. Several tests below exist only
to hold that separation in place, because collapsing the two is the easy and
invisible mistake: every figure still computes, and the number that moves points
at the wrong stage.

Alignment is a schema-constrained model call, so per the replay-first invariant
these tests inject the recorded response and make no live call.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from acceptance.benchmark.case import (
    GroundTruthDefect,
    GroundTruthLabels,
    GroundTruthObligation,
)
from acceptance.benchmark.defect_scoring import (
    align_defects,
    enumeration_recall,
    kill_agreement,
    mapping_from_defects,
    other_share,
    recall_by_type,
    score_defects,
    type_agreement,
)
from acceptance.benchmark.fixtures import load_labels
from acceptance.benchmark.twin_splitting import twin_pairs
from acceptance.review_state import Defect, DefectType
from tests.support import client_dispatching, client_returning

ARCHETYPES = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"


def _obligation(oid: str, description: str = "d", tests: list[str] | None = None, **kwargs):
    return GroundTruthObligation(
        id=oid,
        description=description,
        explicit=True,
        evidence_class="partially_supported",
        evidence_rationale="because",
        candidate_tests=tests if tests is not None else [],
        **kwargs,
    )


def _labelled(did: str, oid: str = "o1", dtype=DefectType.MISSING_CASE, killed=None, desc="x"):
    return GroundTruthDefect(
        id=did, obligation_id=oid, type=dtype, description=desc, killed_by=killed or []
    )


def _recorded(did: str, oid: str = "o1", dtype=DefectType.MISSING_CASE, desc="x"):
    return Defect(id=did, obligation_id=oid, type=dtype, description=desc)


# --- the label format rejects what it cannot score ---


def test_defect_naming_an_undefined_obligation_is_rejected():
    # Not merely wrong: unscoreable and silently so. The label can never be
    # matched, so it depresses enumeration recall forever while reading as a
    # real miss by the enumerator.
    with pytest.raises(ValidationError, match="unknown obligation"):
        GroundTruthLabels(
            obligations=[_obligation("o1")],
            defects=[_labelled("d1", oid="no-such-obligation")],
        )


def test_defect_killed_by_a_test_the_case_does_not_supply_is_rejected():
    with pytest.raises(ValidationError, match="no obligation lists as a candidate test"):
        GroundTruthLabels(
            obligations=[_obligation("o1", tests=["t.py::a"])],
            defects=[_labelled("d1", killed=["t.py::typo"])],
        )


def test_duplicate_defect_ids_are_rejected():
    with pytest.raises(ValidationError, match="defect ids must be unique"):
        GroundTruthLabels(
            obligations=[_obligation("o1")],
            defects=[_labelled("d1"), _labelled("d1")],
        )


def test_no_plausible_defect_is_distinguishable_from_saying_nothing():
    """The label for "nothing is plausible here" must not read as "unlabelled".

    Without the distinction, a case that takes no position scores an enumerator
    that invented three defects exactly like one that correctly recorded none —
    which is DefectSet's own "nothing found" versus "not looked at" rule, on the
    labelling side.
    """
    silent = _obligation("o1")
    reasoned = _obligation("o2", no_plausible_defect_reason="true by construction")

    assert silent.no_plausible_defect_reason is None
    assert reasoned.no_plausible_defect_reason == "true by construction"
    assert silent.no_plausible_defect_reason != reasoned.no_plausible_defect_reason


def test_empty_no_plausible_defect_reason_is_rejected():
    # An empty string would collapse the distinction the test above holds open.
    with pytest.raises(ValidationError, match="omit the field to take no position"):
        GroundTruthLabels(obligations=[_obligation("o1", no_plausible_defect_reason="  ")])


def test_no_plausible_defect_cannot_coexist_with_a_labelled_defect():
    with pytest.raises(ValidationError, match="also carries labelled defects"):
        GroundTruthLabels(
            obligations=[_obligation("o1", no_plausible_defect_reason="none plausible")],
            defects=[_labelled("d1", oid="o1")],
        )


# --- matching is on the described mistake, not the wording ---


def test_a_reworded_defect_still_matches_its_label():
    labelled = [_labelled("d1", desc="The daily rate divides by a hard-coded 30")]
    recorded = [_recorded("r1", desc="Rate uses a fixed 30-day month instead of days_in_month")]
    response = {"matches": [{"labelled": "l0", "recorded": "r0"}]}

    alignment = align_defects(labelled, recorded, client_returning(response))

    assert alignment == {"r1": "d1"}


def test_alignment_is_bijective_so_a_second_claim_on_one_label_is_dropped():
    labelled = [_labelled("d1")]
    recorded = [_recorded("r1"), _recorded("r2")]
    response = {
        "matches": [
            {"labelled": "l0", "recorded": "r0"},
            {"labelled": "l0", "recorded": "r1"},
        ]
    }

    alignment = align_defects(labelled, recorded, client_returning(response))

    assert alignment == {"r1": "d1"}


# --- a type disagreement is a match, not a miss ---


def test_wrong_classification_counts_as_matched_not_as_missed():
    """The failure this guards against sends the fix to the wrong stage.

    A defect recorded with the right description and the wrong type is a
    taxonomy problem. Scored as a miss it reads as an enumerator that did not
    find the defect at all, and the enumerator is then "fixed" for something it
    got right.
    """
    labelled = [_labelled("d1", dtype=DefectType.BOUNDARY_WRONG_SIDE)]
    recorded = [_recorded("r1", dtype=DefectType.MISSING_CASE)]
    alignment = {"r1": "d1"}

    assert enumeration_recall(labelled, alignment) == 1.0
    assert type_agreement(labelled, recorded, alignment) == 0.0


# --- recall and kill agreement do not touch each other ---


def test_recall_and_kill_agreement_are_computed_independently():
    """Vary each input in turn; only its own figure moves.

    Sharing a denominator between the two is the mistake #252 describes — a
    thinner enumeration earning a stronger rating — and it would be invisible,
    because both numbers still compute.
    """
    labelled = [
        _labelled("d1", killed=["t.py::a"]),
        _labelled("d2", killed=["t.py::b"]),
    ]
    both_matched = {"r1": "d1", "r2": "d2"}
    one_matched = {"r1": "d1"}
    right = {"r1": {"t.py::a"}, "r2": {"t.py::b"}}
    wrong = {"r1": {"t.py::z"}, "r2": {"t.py::z"}}

    # Enumeration changes, kill agreement does not: the defect that dropped out
    # of the alignment leaves the kill denominator too, rather than scoring 0.
    assert enumeration_recall(labelled, both_matched) == 1.0
    assert enumeration_recall(labelled, one_matched) == 0.5
    assert kill_agreement(labelled, both_matched, right) == 1.0
    assert kill_agreement(labelled, one_matched, right) == 1.0

    # Predictions change, enumeration does not.
    assert kill_agreement(labelled, both_matched, wrong) == 0.0
    assert enumeration_recall(labelled, both_matched) == 1.0


def test_recall_never_reads_the_predictions():
    labelled = [_labelled("d1", killed=["t.py::a"])]
    alignment = {"r1": "d1"}

    # `enumeration_recall` takes no prediction argument at all, which is the
    # structural half of the guarantee the test above makes behaviourally.
    assert enumeration_recall(labelled, alignment) == 1.0


# --- absent, never zero ---


def test_figures_with_nothing_to_compute_from_are_absent():
    assert enumeration_recall([], {}) is None
    assert type_agreement([], [], {}) is None
    assert other_share([]) is None
    # No prediction supplied at all — the state before #314 exists. Zero would
    # read as a stage that predicts badly rather than one that has not run.
    assert kill_agreement([_labelled("d1")], {"r1": "d1"}, None) is None
    assert kill_agreement([_labelled("d1")], {"r1": "d1"}, {}) is None


def test_a_type_with_no_labelled_defect_is_absent_from_recall_by_type():
    labelled = [_labelled("d1", dtype=DefectType.MISSING_CASE)]

    by_type = recall_by_type(labelled, {})

    assert by_type == {DefectType.MISSING_CASE: 0.0}
    assert DefectType.BOUNDARY_WRONG_SIDE not in by_type


# --- predicting "no test catches this" is a correct prediction ---


def test_predicting_no_killer_for_an_uncaught_defect_scores_as_exact():
    """Archetype 4's shape, and the one the corpus most needs covered.

    A labelled defect that no test kills is the finding the review exists to
    produce. Under the usual undefined-on-empty convention it would drop out of
    the figure entirely.
    """
    labelled = [_labelled("d1", killed=[])]

    assert kill_agreement(labelled, {"r1": "d1"}, {"r1": set()}) == 1.0
    assert kill_agreement(labelled, {"r1": "d1"}, {"r1": {"t.py::a"}}) == 0.0


# --- every figure against hand-computed values ---


def test_every_figure_matches_the_hand_computed_value():
    """One small set worked out by hand, in the comments beside each assertion."""
    labelled = [
        _labelled("d1", dtype=DefectType.MISSING_CASE, killed=["t.py::a"]),
        _labelled("d2", dtype=DefectType.MISSING_CASE, killed=["t.py::a", "t.py::b"]),
        _labelled("d3", dtype=DefectType.BOUNDARY_WRONG_SIDE, killed=[]),
        _labelled("d4", dtype=DefectType.BOUNDARY_WRONG_SIDE, killed=["t.py::c"]),
    ]
    recorded = [
        _recorded("r1", dtype=DefectType.MISSING_CASE),
        _recorded("r2", dtype=DefectType.BOUNDARY_WRONG_SIDE),  # type disagrees with d2
        _recorded("r3", dtype=DefectType.BOUNDARY_WRONG_SIDE),
        _recorded("r4", dtype=DefectType.OTHER),
    ]
    alignment = {"r1": "d1", "r2": "d2", "r3": "d3"}  # d4 missed; r4 spurious
    predicted = {
        "r1": {"t.py::a"},  # exact
        "r2": {"t.py::a"},  # 1 of 2 -> 1/2
        "r3": set(),  # empty vs empty -> exact
    }

    score = score_defects(labelled, recorded, alignment, predicted)

    # 3 of 4 labelled defects matched.
    assert score.enumeration_recall == 0.75
    # missing_case: d1 and d2 both matched -> 1.0. boundary: d3 matched, d4 not -> 0.5.
    assert score.recall_by_type == {
        DefectType.MISSING_CASE: 1.0,
        DefectType.BOUNDARY_WRONG_SIDE: 0.5,
    }
    # 3 matched pairs; r1/d1 agrees, r2/d2 does not, r3/d3 agrees -> 2/3.
    assert score.type_agreement == pytest.approx(2 / 3)
    # 1 of 4 recorded defects is `other`.
    assert score.other_share == 0.25
    # jaccard 1.0, 0.5, 1.0 over the three matched defects with a prediction.
    assert score.kill_agreement == pytest.approx(2.5 / 3)
    assert (score.labelled, score.recorded, score.matched, score.predicted) == (4, 4, 3, 3)


# --- scoring makes no model call ---


def test_scoring_makes_no_model_call():
    """`score_defects` takes an alignment, never a client.

    Passing a client that raises on use would only prove this module does not
    call *that* client; taking no client at all is the property itself. The one
    model judgement is `align_defects`, which the caller runs once.
    """
    import inspect

    for fn in (score_defects, enumeration_recall, kill_agreement, type_agreement, other_share):
        params = set(inspect.signature(fn).parameters)
        assert "client" not in params, f"{fn.__name__} takes a client"

    exploding = client_returning({"matches": []})
    exploding.complete = lambda *a, **k: pytest.fail("scoring issued a model call")

    score_defects([_labelled("d1")], [_recorded("r1")], {"r1": "d1"}, {"r1": set()})


# --- the split measure, recomputed over defect-derived edges ---


def test_split_measure_runs_over_tests_reached_through_defects():
    """Two obligations stating the same demand, reached by way of their defects.

    The measure itself is unchanged — `mapping_from_defects` only builds the
    input `twin_pairs` already consumes — so the figure stays comparable across
    the change in how an obligation reaches a test.
    """
    obligations = [
        _obligation("o1", "Round to two decimals"),
        _obligation("o2", "Round to two decimals"),
    ]
    recorded = [_recorded("r1", oid="o1"), _recorded("r2", oid="o2")]
    predicted = {"r1": {"t.py::a"}, "r2": {"t.py::b"}}

    mapping = mapping_from_defects("synthetic", obligations, recorded, predicted)
    pairs = twin_pairs(mapping)

    assert len(pairs) == 1
    assert pairs[0].identical is True
    assert pairs[0].shared == 0
    assert pairs[0].split == 2  # a and b, each reached by exactly one side


def test_an_obligation_with_no_prediction_reaches_no_test():
    obligations = [
        _obligation("o1", "Round to two decimals"),
        _obligation("o2", "Round to two decimals"),
    ]
    recorded = [_recorded("r1", oid="o1"), _recorded("r2", oid="o2")]

    mapping = mapping_from_defects("synthetic", obligations, recorded, None)

    assert mapping.mapped_tests == {0: [], 1: []}
    assert twin_pairs(mapping)[0].opportunities == 0


# --- the shipped labels ---


@pytest.mark.parametrize("case_dir", sorted(p.name for p in ARCHETYPES.iterdir() if p.is_dir()))
def test_every_archetype_label_set_loads_and_validates(case_dir):
    labels = load_labels(ARCHETYPES / case_dir)

    assert labels.defects, f"{case_dir} carries no defect labels"
    for defect in labels.defects:
        assert defect.description.strip()


def test_archetype_four_labels_its_non_discriminating_defect_as_uncaught():
    """The case the whole defect-first change exists for.

    A hard-coded 30-day divisor that the only test cannot distinguish. If this
    label ever gains a killing test, the fixture has stopped being an example of
    a non-discriminating input.
    """
    labels = load_labels(ARCHETYPES / "04-non-discriminating-input")

    defect = next(d for d in labels.defects if d.id == "d-hard-coded-thirty-day-month")
    assert defect.obligation_id == "daily-rate"
    assert defect.killed_by == []


# --- the pipeline actually calls it ---


def _scoreable_case(labelled, defect_sets):
    """A minimal case `score_case` will accept, carrying defect labels and a
    review that recorded defects."""
    from acceptance.benchmark.case import (
        BenchmarkCase,
        BenchmarkCaseInputs,
        BenchmarkCaseSource,
    )
    from acceptance.review_state import (
        DeterminismControls,
        Obligation,
        ObligationType,
        Review,
        ReviewProvenance,
    )

    return BenchmarkCase(
        case_id="wiring",
        source=BenchmarkCaseSource(kind="archetype", identifier="wiring"),
        inputs=BenchmarkCaseInputs(repo="r", task_text="t", base_revision="a", head_revision="b"),
        ground_truth=GroundTruthLabels(
            obligations=[_obligation("o1", "Round the total to two decimals")],
            defects=labelled,
        ),
        reviewer_output=Review(
            mode="local",
            reviewed_revision="b",
            provenance=ReviewProvenance(
                determinism_mode="replay",
                model="m",
                controls_requested=DeterminismControls(temperature=0.0),
            ),
            obligation_map=[
                Obligation(
                    id="o1",
                    description="Round the total to two decimals",
                    type=ObligationType.FUNCTIONAL,
                    importance="critical",
                    explicit=True,
                    observable_behavior="...",
                )
            ],
            defect_sets=defect_sets,
        ),
    )


def test_score_case_populates_the_defect_figures():
    """The wiring, not the function.

    `score_defects` having a passing unit test says nothing about whether the
    scorer ever calls it — the shape of hole defect injection keeps finding in
    this repo.
    """
    from acceptance.benchmark.scoring import score_case
    from acceptance.review_state import DefectSet

    case = _scoreable_case(
        labelled=[_labelled("d1", oid="o1", desc="The total is not rounded")],
        defect_sets=[DefectSet(obligation_id="o1", defects=[_recorded("r1", oid="o1")])],
    )
    client = client_dispatching(
        {
            "_Alignment": {"matches": []},
            "_DefectAlignment": {"matches": [{"labelled": "l0", "recorded": "r0"}]},
        }
    )

    score = score_case(case, client)

    assert score.defects is not None
    assert score.defects.enumeration_recall == 1.0
    assert score.defects.labelled == 1
    assert score.defects.matched == 1
    # Nothing supplies a prediction yet; absent, not zero.
    assert score.defects.kill_agreement is None


def test_an_enumerator_that_recorded_nothing_scores_zero_not_absent():
    """A total enumeration miss is a result, not a blank.

    Reported as absent it would look exactly like a case the ground truth takes
    no position on, so the worst enumeration outcome the corpus can show would
    be indistinguishable from having nothing to say. Found by the Gate 2 run on
    this issue's own change.
    """
    from acceptance.benchmark.scoring import score_case

    case = _scoreable_case(
        labelled=[_labelled("d1", oid="o1", desc="The total is not rounded")],
        defect_sets=[],
    )
    # No client at all: with one side empty there is nothing to align, so the
    # figure is still computable and must still be computed.
    score = score_case(case, None)

    assert score.defects is not None
    assert score.defects.enumeration_recall == 0.0
    assert score.defects.labelled == 1
    assert score.defects.recorded == 0
    assert score.defects.matched == 0
    # These genuinely have nothing to compute from and stay absent.
    assert score.defects.type_agreement is None
    assert score.defects.other_share is None


def test_no_client_leaves_the_figures_absent_rather_than_scoring_every_match_a_miss():
    from acceptance.benchmark.scoring import score_case
    from acceptance.review_state import DefectSet

    case = _scoreable_case(
        labelled=[_labelled("d1", oid="o1", desc="The total is not rounded")],
        defect_sets=[DefectSet(obligation_id="o1", defects=[_recorded("r1", oid="o1")])],
    )

    score = score_case(case, None)

    # Both sides have content, but nothing can match them. A 0.0 here would be a
    # measurement artefact reported as an enumerator failure.
    assert score.defects is None


def test_score_case_leaves_the_defect_figures_absent_with_no_labels():
    """And spends no model call doing it."""
    from acceptance.benchmark.scoring import score_case
    from acceptance.review_state import DefectSet

    case = _scoreable_case(
        labelled=[],
        defect_sets=[DefectSet(obligation_id="o1", defects=[_recorded("r1", oid="o1")])],
    )
    client = client_dispatching({"_Alignment": {"matches": []}})

    score = score_case(case, client)

    assert score.defects is None


def test_labels_json_defect_ids_are_unique_within_each_case():
    for case_dir in sorted(p for p in ARCHETYPES.iterdir() if p.is_dir()):
        raw = json.loads((case_dir / "labels.json").read_text())
        ids = [d["id"] for d in raw.get("defects", [])]
        assert len(ids) == len(set(ids)), case_dir.name
