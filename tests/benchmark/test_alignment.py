"""#118: semantic obligation alignment, and semantic scoring built on it.

Alignment is a schema-constrained model call; per the replay-first invariant
these tests inject the recorded response — no live calls. The point being
proven: a correct-but-REWORDED reviewer criterion counts as matched, where an
exact-string join would score it 0.
"""

from acceptance.benchmark.alignment import align_obligations
from acceptance.benchmark.case import (
    BenchmarkCase,
    BenchmarkCaseInputs,
    BenchmarkCaseSource,
    GroundTruthGap,
    GroundTruthLabels,
    GroundTruthObligation,
)
from acceptance.benchmark.scoring import score_case
from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.review_state import (
    DeterminismControls,
    Finding,
    Link,
    Obligation,
    ObligationType,
    Review,
    ReviewProvenance,
)
from tests.support import client_returning


# --- align_obligations ---


def test_reworded_criteria_are_aligned():
    gt = ["Daily rate is monthly_price divided by days_in_month"]
    rv = ["Use monthly_price / days_in_month as the daily rate"]
    response = {"matches": [{"ground_truth": "g0", "reviewer": "r0"}]}

    alignment = align_obligations(gt, rv, client_returning(response))

    assert alignment == {rv[0]: gt[0]}


def test_alignment_is_bijective_extra_reviewer_criterion_is_dropped():
    # Two reviewer criteria claim the same ground-truth criterion (over-
    # decomposition); only the first match is kept, so the extra stays unmatched.
    gt = ["A"]
    rv = ["A prime", "A double-prime"]
    response = {"matches": [
        {"ground_truth": "g0", "reviewer": "r0"},
        {"ground_truth": "g0", "reviewer": "r1"},
    ]}

    alignment = align_obligations(gt, rv, client_returning(response))

    assert alignment == {"A prime": "A"}


def test_unknown_labels_are_ignored():
    alignment = align_obligations(
        ["A"], ["B"], client_returning({"matches": [{"ground_truth": "g9", "reviewer": "r0"}]})
    )
    assert alignment == {}


def test_empty_sides_make_no_call():
    # No obligations on a side -> no possible match, no model call needed.
    import tempfile
    from acceptance.llm import Mode, ModelClient, TranscriptStore

    def boom(**kwargs):
        raise AssertionError("no model call should be made with an empty side")

    client = ModelClient(model="x", mode=Mode.RECORD,
                         store=TranscriptStore(tempfile.mkdtemp()), completion_fn=boom)
    assert align_obligations([], ["A"], client) == {}
    assert align_obligations(["A"], [], client) == {}


# --- semantic scoring built on the alignment ---


def _reviewer_obligation(description: str) -> Obligation:
    return Obligation(id=description.lower().replace(" ", "-"), description=description,
                      type=ObligationType.FUNCTIONAL, importance="critical", explicit=True,
                      observable_behavior="...")


def _case_with_reworded_reviewer_output() -> BenchmarkCase:
    ground_truth = GroundTruthLabels(
        obligations=[
            GroundTruthObligation(
                id="daily-rate", description="Daily rate is monthly_price divided by days_in_month",
                explicit=True, evidence_class="strongly_supported", evidence_rationale="asserted",
                candidate_tests=["test_billing.py::test_rate"],
            ),
        ],
        gaps=[GroundTruthGap(id="g", description="rate wrong", obligation_id="daily-rate")],
    )
    reviewer = Review(
        mode="local", reviewed_revision="def456",
        provenance=ReviewProvenance(
            determinism_mode="replay", model="m",
            controls_requested=DeterminismControls(temperature=0.0),
        ),
        obligation_map=[
            # Same criterion, different wording, AND its mapped test.
            _reviewer_obligation("Use monthly_price / days_in_month as the daily rate").model_copy(
                update={"test_evidence": ["test_billing.py::test_rate"]}
            ),
        ],
        findings=[Finding(
            type="coverage_gap", severity="high", description="rate not established",
            evidence_tier=EvidenceTier.STATIC, produced_by=Component.STATIC_ANALYZER,
            links=[Link(kind="requirement", ref="task.md:1")],
            related_obligation="Use monthly_price / days_in_month as the daily rate",
        )],
    )
    return BenchmarkCase(
        case_id="reworded",
        source=BenchmarkCaseSource(kind="archetype", identifier="reworded"),
        inputs=BenchmarkCaseInputs(repo="r", task_text="...", base_revision="a", head_revision="def456"),
        ground_truth=ground_truth,
        reviewer_output=reviewer,
    )


def test_exact_match_scores_reworded_output_as_zero():
    # Baseline: with no client, the reworded criterion doesn't string-match.
    case = _case_with_reworded_reviewer_output()

    score = score_case(case)  # no client -> exact match

    assert score.decomposition_accuracy == 0.0
    assert score.mapping_accuracy == 0.0
    assert score.gap_recall == 0.0


def test_semantic_match_scores_reworded_output_correctly():
    case = _case_with_reworded_reviewer_output()
    # The aligner matches the single reworded reviewer criterion to the gt one.
    client = client_returning({"matches": [{"ground_truth": "g0", "reviewer": "r0"}]})

    score = score_case(case, client)

    assert score.decomposition_accuracy == 1.0
    assert score.mapping_accuracy == 1.0
    assert score.gap_recall == 1.0
