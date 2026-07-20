import json

import pytest

from acceptance.benchmark.case import (
    BenchmarkCase,
    BenchmarkCaseInputs,
    BenchmarkCaseSource,
    BenchmarkScore,
    GroundTruthDecompositionItem,
    GroundTruthEvidenceClass,
    GroundTruthGap,
    GroundTruthLabels,
    GroundTruthMapping,
)
from acceptance.review_state import Review


def _round_trip(instance):
    cls = type(instance)
    persisted = json.loads(json.dumps(instance.to_dict()))
    return cls.from_dict(persisted)


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
        ground_truth=GroundTruthLabels(
            gaps=[GroundTruthGap(description="Active filters not applied")]
        ),
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


def test_case_missing_ground_truth_entirely_fails_validation():
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


def test_empty_ground_truth_labels_fails_validation():
    with pytest.raises(ValueError):
        GroundTruthLabels()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"gaps": [GroundTruthGap(description="Filter behavior unsupported")]},
        {"decomposition": [GroundTruthDecompositionItem(description="CSV export", explicit=True)]},
        {"mappings": [GroundTruthMapping(test_id="test_csv", obligation_ref="csv-export")]},
        {
            "evidence_classes": [
                GroundTruthEvidenceClass(obligation_ref="csv-export", classification="unsupported")
            ]
        },
    ],
)
def test_each_ground_truth_category_alone_is_sufficient(kwargs):
    labels = GroundTruthLabels(**kwargs)
    assert _round_trip(labels) == labels


def test_ground_truth_evidence_classification_rejects_unknown_value():
    with pytest.raises(ValueError):
        GroundTruthLabels(
            evidence_classes=[
                GroundTruthEvidenceClass(obligation_ref="csv-export", classification="bogus")
            ]
        )


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
