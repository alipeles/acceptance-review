"""M-B0.3 acceptance: on a synthetic set with known labels, computed metrics
match hand-calculated expected values.

Case A: gap ground truth {filters, row-limit}; reviewer reports {filters}.
  -> gap: matched=1, gt=2, reported=1
Case B: gap ground truth {csv-escaping}; reviewer reports {csv-escaping, unrelated}.
  -> gap: matched=1, gt=1, reported=2
Pooled: matched=2, gt=3, reported=3 -> gap_recall = 2/3, gap_precision = 2/3

Case A decomposition ground truth {"CSV generation", "Active filters applied"};
  reviewer reports {"CSV generation"}. -> matched=1, gt=2
Case B decomposition ground truth {"Escape special characters"};
  reviewer reports {"Escape special characters"}. -> matched=1, gt=1
Pooled: matched=2, gt=3 -> decomposition_accuracy = 2/3

Case A mapping ground truth {(test_csv, "CSV generation")}; reviewer reports
  the same pair via Obligation.test_evidence. -> matched=1, gt=1
Case B mapping ground truth {(test_escape, escaping)}; reviewer reports nothing.
  -> matched=0, gt=1
Pooled: matched=1, gt=2 -> mapping_accuracy = 1/2

evidence_classes: Case A has 1 ground-truth label, Case B has none.
Pooled ground truth=1, matched=0 (Finding can't express a classification yet)
  -> evidence_agreement = 0/1 = 0.0
"""

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
from acceptance.benchmark.scoring import score_case_set
from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.review_state import Finding, Link, Obligation, Review, ReviewProvenance


def _inputs() -> BenchmarkCaseInputs:
    return BenchmarkCaseInputs(
        repo="fixtures/synthetic",
        task_text="## Deliverable\n...\n",
        base_revision="abc123",
        head_revision="def456",
    )


def _provenance() -> ReviewProvenance:
    return ReviewProvenance(
        determinism_mode="replay", model="anthropic/claude-sonnet-5", temperature=0.0
    )


def _case_a() -> BenchmarkCase:
    return BenchmarkCase(
        case_id="synthetic-a",
        source=BenchmarkCaseSource(kind="archetype", identifier="synthetic-a"),
        inputs=_inputs(),
        ground_truth=GroundTruthLabels(
            gaps=[
                GroundTruthGap(description="filters missing", obligation_ref="filters"),
                GroundTruthGap(description="row limit missing", obligation_ref="row-limit"),
            ],
            decomposition=[
                GroundTruthDecompositionItem(description="CSV generation", explicit=True),
                GroundTruthDecompositionItem(description="Active filters applied", explicit=True),
            ],
            mappings=[GroundTruthMapping(test_id="test_csv", obligation_ref="CSV generation")],
            evidence_classes=[
                GroundTruthEvidenceClass(
                    obligation_ref="CSV generation", classification="strongly_supported"
                )
            ],
        ),
        reviewer_output=Review(
            mode="local",
            reviewed_revision="def456",
            provenance=_provenance(),
            obligation_map=[
                Obligation(
                    description="CSV generation",
                    type="behavior",
                    source_text="...",
                    importance="critical",
                    explicit=True,
                    observable_behavior="...",
                    test_evidence=["test_csv"],
                )
            ],
            findings=[
                Finding(
                    type="missed_obligation",
                    severity="high",
                    description="Filters not applied",
                    evidence_tier=EvidenceTier.STATIC,
                    produced_by=Component.STATIC_ANALYZER,
                    links=[Link(kind="requirement", ref="task.md:1")],
                    related_obligation="filters",
                )
            ],
        ),
    )


def _case_b() -> BenchmarkCase:
    return BenchmarkCase(
        case_id="synthetic-b",
        source=BenchmarkCaseSource(kind="archetype", identifier="synthetic-b"),
        inputs=_inputs(),
        ground_truth=GroundTruthLabels(
            gaps=[GroundTruthGap(description="csv escaping missing", obligation_ref="csv-escaping")],
            decomposition=[
                GroundTruthDecompositionItem(description="Escape special characters", explicit=True)
            ],
            mappings=[GroundTruthMapping(test_id="test_escape", obligation_ref="escaping")],
        ),
        reviewer_output=Review(
            mode="local",
            reviewed_revision="def456",
            provenance=_provenance(),
            obligation_map=[
                Obligation(
                    description="Escape special characters",
                    type="behavior",
                    source_text="...",
                    importance="critical",
                    explicit=True,
                    observable_behavior="...",
                    # No test_evidence: the mapping ground truth goes unmatched.
                )
            ],
            findings=[
                Finding(
                    type="missed_obligation",
                    severity="high",
                    description="CSV escaping not handled",
                    evidence_tier=EvidenceTier.STATIC,
                    produced_by=Component.STATIC_ANALYZER,
                    links=[Link(kind="requirement", ref="task.md:2")],
                    related_obligation="csv-escaping",
                ),
                Finding(
                    type="missed_obligation",
                    severity="low",
                    description="Spurious, unrelated finding",
                    evidence_tier=EvidenceTier.STATIC,
                    produced_by=Component.STATIC_ANALYZER,
                    links=[Link(kind="requirement", ref="task.md:3")],
                    related_obligation="unrelated",
                ),
            ],
        ),
    )


def test_pooled_report_matches_hand_calculated_values():
    report = score_case_set([_case_a(), _case_b()])

    assert report.case_count == 2
    assert report.determinism_mode == "replay"
    assert report.gap_recall == 2 / 3
    assert report.gap_precision == 2 / 3
    assert report.decomposition_accuracy == 2 / 3
    assert report.mapping_accuracy == 1 / 2
    assert report.evidence_agreement == 0.0


def test_report_includes_per_case_scores():
    report = score_case_set([_case_a(), _case_b()])

    assert len(report.per_case) == 2
    # Case A alone: gap matched=1, gt=2, reported=1.
    assert report.per_case[0].gap_recall == 0.5
    assert report.per_case[0].gap_precision == 1.0
    # Case B alone: gap matched=1, gt=1, reported=2.
    assert report.per_case[1].gap_recall == 1.0
    assert report.per_case[1].gap_precision == 0.5


def test_empty_case_set_yields_no_metrics():
    report = score_case_set([])

    assert report.case_count == 0
    assert report.determinism_mode is None
    assert report.gap_recall is None
    assert report.gap_precision is None
    assert report.decomposition_accuracy is None
    assert report.mapping_accuracy is None
    assert report.evidence_agreement is None
    assert report.per_case == []


def test_case_set_raises_if_any_case_has_no_reviewer_output():
    unrun_case = _case_a().model_copy(update={"reviewer_output": None})
    with pytest.raises(ValueError):
        score_case_set([unrun_case])


def test_case_set_raises_if_a_case_has_no_provenance():
    case = _case_a()
    unstamped = case.model_copy(
        update={"reviewer_output": case.reviewer_output.model_copy(update={"provenance": None})}
    )
    with pytest.raises(ValueError):
        score_case_set([unstamped])


def test_case_set_raises_on_mixed_determinism_modes():
    case_a = _case_a()
    recorded_provenance = _provenance().model_copy(update={"determinism_mode": "record"})
    case_a_recorded = case_a.model_copy(
        update={
            "reviewer_output": case_a.reviewer_output.model_copy(
                update={"provenance": recorded_provenance}
            )
        }
    )

    with pytest.raises(ValueError):
        score_case_set([case_a_recorded, _case_b()])
