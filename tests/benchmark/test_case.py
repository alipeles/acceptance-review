import json

import pytest

from acceptance.benchmark.case import (
    BenchmarkCase,
    BenchmarkCaseInputs,
    BenchmarkCaseSource,
    BenchmarkScore,
    GroundTruthGap,
    GroundTruthLabels,
    GroundTruthObligation,
)
from acceptance.review_state import Review


def _round_trip(instance):
    cls = type(instance)
    persisted = json.loads(json.dumps(instance.to_dict()))
    return cls.from_dict(persisted)


def _obligation(**overrides) -> GroundTruthObligation:
    defaults = dict(
        id="csv-generation",
        description="CSV generation",
        explicit=True,
        evidence_class="strongly_supported",
        evidence_rationale="The test asserts the generated CSV exactly.",
        candidate_tests=["test_csv.py::test_basic"],
    )
    defaults.update(overrides)
    return GroundTruthObligation(**defaults)


def _labels(**overrides) -> GroundTruthLabels:
    defaults = dict(
        obligations=[
            _obligation(),
            _obligation(id="filters", description="Active filters applied",
                        evidence_class="unsupported",
                        evidence_rationale="No test exercises filtering.", candidate_tests=[]),
        ],
        gaps=[
            GroundTruthGap(
                id="gap-filters",
                description="Active filters not applied",
                obligation_id="filters",
                severity="high",
            )
        ],
    )
    defaults.update(overrides)
    return GroundTruthLabels(**defaults)


def _case(**overrides) -> BenchmarkCase:
    defaults = dict(
        case_id="archetype-01",
        source=BenchmarkCaseSource(kind="archetype", identifier="missed-obligation"),
        inputs=BenchmarkCaseInputs(
            repo="fixtures/archetype-01",
            task_text="## Deliverable\nAdd CSV export.\n",
            base_revision="abc123",
            head_revision="def456",
        ),
        ground_truth=_labels(),
    )
    defaults.update(overrides)
    return BenchmarkCase(**defaults)


def test_benchmark_case_round_trips():
    case = _case()
    assert _round_trip(case) == case


def test_benchmark_case_round_trips_with_reviewer_output_and_score():
    case = _case(
        reviewer_output=Review(mode="local", reviewed_revision="def456"),
        score=BenchmarkScore(gap_recall=1.0, gap_precision=0.5),
    )
    assert _round_trip(case) == case


def test_labels_round_trip():
    labels = _labels()
    assert _round_trip(labels) == labels


def test_case_with_no_obligations_fails_validation():
    with pytest.raises(ValueError):
        GroundTruthLabels(obligations=[], gaps=[])


def test_case_requires_ground_truth():
    with pytest.raises(ValueError):
        BenchmarkCase(
            case_id="archetype-01",
            source=BenchmarkCaseSource(kind="archetype", identifier="missed-obligation"),
            inputs=BenchmarkCaseInputs(
                repo="fixtures/archetype-01",
                task_text="...",
                base_revision="abc123",
                head_revision="def456",
            ),
        )


def test_gap_referencing_unknown_obligation_fails_validation():
    with pytest.raises(ValueError):
        GroundTruthLabels(
            obligations=[_obligation()],
            gaps=[GroundTruthGap(id="g1", description="x", obligation_id="does-not-exist")],
        )


def test_gap_with_no_obligation_id_is_allowed():
    labels = GroundTruthLabels(
        obligations=[_obligation()],
        gaps=[GroundTruthGap(id="g1", description="a declaration overclaim", obligation_id=None)],
    )
    assert labels.gaps[0].obligation_id is None


def test_duplicate_obligation_ids_fail_validation():
    with pytest.raises(ValueError):
        GroundTruthLabels(obligations=[_obligation(), _obligation()])


def test_duplicate_gap_ids_fail_validation():
    with pytest.raises(ValueError):
        GroundTruthLabels(
            obligations=[_obligation()],
            gaps=[
                GroundTruthGap(id="g1", description="a"),
                GroundTruthGap(id="g1", description="b"),
            ],
        )


def test_empty_candidate_test_id_fails_validation():
    with pytest.raises(ValueError):
        GroundTruthLabels(obligations=[_obligation(candidate_tests=[""])])


def test_missing_evidence_rationale_fails_validation():
    with pytest.raises(ValueError):
        GroundTruthLabels(obligations=[_obligation(evidence_rationale="  ")])


def test_unknown_evidence_classification_is_rejected():
    with pytest.raises(ValueError):
        _obligation(evidence_class="bogus")


def test_benchmark_case_source_round_trips():
    source = BenchmarkCaseSource(kind="real_pr", identifier="https://github.com/org/repo/pull/1")
    assert _round_trip(source) == source


def test_benchmark_case_inputs_round_trips_with_declaration():
    inputs = BenchmarkCaseInputs(
        repo="org/repo",
        task_text="...",
        base_revision="abc123",
        head_revision="def456",
        declaration_text="## Mandate as understood\n...",
    )
    assert _round_trip(inputs) == inputs
