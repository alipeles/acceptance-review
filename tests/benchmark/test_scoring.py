import pytest

from acceptance.benchmark.case import (
    BenchmarkCase,
    BenchmarkCaseInputs,
    BenchmarkCaseSource,
    GroundTruthDecompositionItem,
    GroundTruthEvidenceClass,
    GroundTruthGap,
    GroundTruthLabels,
    GroundTruthMapping,
)
from acceptance.benchmark.scoring import score_case
from acceptance.review_state import Review


def _archetype_case(**overrides) -> BenchmarkCase:
    defaults = dict(
        case_id="archetype-01-missed-obligation",
        source=BenchmarkCaseSource(kind="archetype", identifier="missed-obligation"),
        inputs=BenchmarkCaseInputs(
            repo="fixtures/archetype-01",
            task_text="## Deliverable\nAdd CSV export with active filters.\n",
            base_revision="abc123",
            head_revision="def456",
        ),
        ground_truth=GroundTruthLabels(
            gaps=[GroundTruthGap(description="Active filters not applied", obligation_ref="filters")],
            decomposition=[
                GroundTruthDecompositionItem(description="CSV generation", explicit=True),
                GroundTruthDecompositionItem(description="Active filters applied", explicit=True),
            ],
            mappings=[GroundTruthMapping(test_id="test_csv_basic", obligation_ref="csv-generation")],
            evidence_classes=[
                GroundTruthEvidenceClass(obligation_ref="csv-generation", classification="strongly_supported")
            ],
        ),
    )
    defaults.update(overrides)
    return BenchmarkCase(**defaults)


def test_score_case_raises_without_reviewer_output():
    case = _archetype_case()
    with pytest.raises(ValueError):
        score_case(case)


def test_empty_review_yields_an_all_miss_score():
    case = _archetype_case(
        reviewer_output=Review(mode="local", reviewed_revision="def456")
    )

    score = score_case(case)

    # Ground truth exists but nothing was reported: real, computable zeros.
    assert score.gap_recall == 0.0
    assert score.decomposition_accuracy == 0.0
    assert score.mapping_accuracy == 0.0
    # evidence_agreement is a real 0.0 too: Finding has no §9.3 classification
    # field yet (M5.3), so nothing can ever be reported for this metric.
    assert score.evidence_agreement == 0.0
    # Nothing was reported to be right or wrong about: undefined, not 0.0/1.0.
    assert score.gap_precision is None


def test_recall_and_precision_are_none_when_ground_truth_is_empty():
    case = _archetype_case(
        ground_truth=GroundTruthLabels(gaps=[GroundTruthGap(description="only gaps present")]),
        reviewer_output=Review(mode="local", reviewed_revision="def456"),
    )

    score = score_case(case)

    # No ground-truth decomposition/mappings/evidence_classes to score against.
    assert score.decomposition_accuracy is None
    assert score.mapping_accuracy is None
    assert score.evidence_agreement is None
