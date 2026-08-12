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
    defaults = {
        "case_id": "archetype-01-missed-obligation",
        "source": BenchmarkCaseSource(kind="archetype", identifier="missed-obligation"),
        "inputs": BenchmarkCaseInputs(
            repo="fixtures/archetype-01",
            task_text="## Deliverable\nAdd CSV export with active filters.\n",
            base_revision="abc123",
            head_revision="def456",
        ),
        "ground_truth": GroundTruthLabels(
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
    }
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
                    id="only",
                    description="only obligation",
                    explicit=True,
                    evidence_class="unsupported",
                    evidence_rationale="No test at all.",
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


# --- #164: the metric carries its own comparability warning ------------------


def _text_around(path, anchor: str, before: int = 8) -> str:
    """The lines immediately preceding `anchor` in `path` — where a field's
    explanatory comment lives in this codebase."""
    import pathlib

    lines = pathlib.Path(path).read_text().splitlines()
    index = next(i for i, line in enumerate(lines) if anchor in line)
    return "\n".join(lines[max(0, index - before) : index + 1])


def test_mapping_accuracy_is_marked_not_comparable_across_the_partitioning_change():
    """A mapping-accuracy figure from before #164 and one from after measure
    different questions being asked of the model, so a reader who plots them as
    a trend draws a conclusion the data cannot support. The warning has to sit
    where the number is met, not only in the decision record — this test fails
    if it is deleted, softened, or drifts away from the field."""
    import acceptance.benchmark.case as case_module
    import acceptance.benchmark.scoring as scoring_module

    report = _text_around(scoring_module.__file__, "    mapping_accuracy: float | None = None")
    score = _text_around(case_module.__file__, "    mapping_accuracy: float | None = None")
    sampled = _text_around(scoring_module.__file__, "    mapping_accuracy: MetricStats")

    for text in (report, score, sampled):
        assert "not comparable" in text.lower()
        assert "#164" in text

    # The strong form: not merely "changed", but "do not compare".
    assert "must not be plotted as a trend" in report
    assert "regression" in report


def test_the_decision_record_states_the_non_comparability_too():
    """The DR is where someone reading the *change* lands, as opposed to
    someone reading the *number*. Both entry points have to carry it."""
    import pathlib

    dr = pathlib.Path(__file__).resolve().parents[2] / "docs"
    text = (dr / "DR-164-mapping-stage-request-partitioning.md").read_text()

    assert "not comparable" in text.lower()
    assert "mapping-accuracy" in text.lower()
