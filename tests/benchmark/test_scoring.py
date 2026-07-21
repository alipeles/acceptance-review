import pytest

from acceptance.benchmark.case import (
    BenchmarkCase,
    BenchmarkCaseInputs,
    BenchmarkCaseSource,
    GroundTruthGap,
    GroundTruthLabels,
    GroundTruthObligation,
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
            obligations=[
                GroundTruthObligation(
                    id="csv-generation",
                    description="CSV generation",
                    explicit=True,
                    evidence_class="strongly_supported",
                    evidence_rationale="The test asserts the generated CSV exactly.",
                    candidate_tests=["test_csv.py::test_basic"],
                ),
                GroundTruthObligation(
                    id="filters",
                    description="Active filters applied",
                    explicit=True,
                    evidence_class="unsupported",
                    evidence_rationale="No test exercises filtering.",
                    candidate_tests=[],
                ),
            ],
            gaps=[
                GroundTruthGap(
                    id="gap-filters",
                    description="Active filters not applied",
                    obligation_id="filters",
                    severity="high",
                )
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
    case = _archetype_case(reviewer_output=Review(mode="local", reviewed_revision="def456"))

    score = score_case(case)

    # Ground truth exists but nothing was reported: real, computable zeros.
    assert score.gap_recall == 0.0
    assert score.decomposition_accuracy == 0.0
    assert score.mapping_accuracy == 0.0
    # evidence_agreement is a real 0.0: a reviewer Obligation has no §9.3
    # classification field yet (M5.3), so nothing can be reported for it.
    assert score.evidence_agreement == 0.0
    # Nothing was reported to be right or wrong about: undefined, not 0.0/1.0.
    assert score.gap_precision is None


def test_metrics_are_none_when_their_ground_truth_is_empty():
    # An obligation with no candidate test and a case with no gaps: mapping has
    # no ground-truth edges, and gaps have none, so both are undefined.
    case = _archetype_case(
        ground_truth=GroundTruthLabels(
            obligations=[
                GroundTruthObligation(
                    id="only", description="only obligation", explicit=True,
                    evidence_class="unsupported", evidence_rationale="No test at all.",
                    candidate_tests=[],
                )
            ],
            gaps=[],
        ),
        reviewer_output=Review(mode="local", reviewed_revision="def456"),
    )

    score = score_case(case)

    assert score.gap_recall is None  # no labeled gaps
    assert score.mapping_accuracy is None  # no candidate_tests edges
    assert score.decomposition_accuracy == 0.0  # one obligation, none reported
    assert score.evidence_agreement == 0.0  # one obligation with an evidence class
