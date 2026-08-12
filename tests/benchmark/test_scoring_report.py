"""M-B0.3 acceptance: on a synthetic set with known labels, computed metrics
match hand-calculated expected values. Recomputed for the M-B5a.2 obligation
tree (each obligation carries its covered_by tests and evidence class).

Two cases with hand-authored reviewer output. Match keys: obligations by
description, mappings by (obligation description, test id), gaps by the
description of the obligation they concern, evidence agreement always
reported_total=0 (no reviewer §9.3 classification yet).

Case A ground truth: obligations {Alpha [T1], Beta []}, gap on Beta,
       unrequested change in x.py.
       reviewer: reports obligation Alpha (but not its T1 mapping); flags Beta;
                 flags an unrequested change in x.py.
  gap:           matched 1, gt 1, reported 1
  decomposition: matched 1 (Alpha), gt 2, reported 1
  mapping:       matched 0, gt 1 (Alpha,T1), reported 0
  evidence:      gt 2, reported 0
  unrequested:   matched 1 (x.py), gt 1, reported 1

Case B ground truth: obligations {Gamma [T2]}, no gaps (true negative), no
       unrequested changes.
       reviewer: reports Gamma with its T2 mapping + a spurious Delta;
                 raises a spurious Epsilon finding; flags a spurious
                 unrequested change in y.py.
  gap:           matched 0, gt 0, reported 1
  decomposition: matched 1 (Gamma), gt 1, reported 2 (Gamma, Delta)
  mapping:       matched 1 (Gamma,T2), gt 1, reported 1
  evidence:      gt 1, reported 0
  unrequested:   matched 0, gt 0, reported 1 (y.py)

Pooled:
  gap_recall    = 1/1 = 1.0     gap_precision = 1/2 = 0.5
  decomposition = 2/3
  mapping       = 1/2 = 0.5
  evidence      = 0/3 = 0.0
  unrequested_recall = 1/1 = 1.0     unrequested_precision = 1/2 = 0.5
"""

import pytest

from acceptance.benchmark.case import (
    BenchmarkCase,
    BenchmarkCaseInputs,
    BenchmarkCaseSource,
    GroundTruthGap,
    GroundTruthLabels,
    GroundTruthObligation,
    GroundTruthUnrequestedChange,
)
from acceptance.benchmark.scoring import score_case_set
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


def _inputs() -> BenchmarkCaseInputs:
    return BenchmarkCaseInputs(
        repo="fixtures/synthetic",
        task_text="## Deliverable\n...\n",
        base_revision="abc123",
        head_revision="def456",
    )


def _provenance() -> ReviewProvenance:
    return ReviewProvenance(
        determinism_mode="replay",
        model="anthropic/claude-sonnet-5",
        controls_requested=DeterminismControls(temperature=0.0),
    )


def _reviewer_obligation(description: str, test_evidence: list[str]) -> Obligation:
    return Obligation(
        id=description.lower(),
        description=description,
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="...",
        test_evidence=test_evidence,
    )


def _finding(related_obligation: str) -> Finding:
    return Finding(
        type="missed_obligation",
        severity="high",
        description=f"gap on {related_obligation}",
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="requirement", ref="task.md:1")],
        related_obligation=related_obligation,
    )


def _unrequested_finding(file: str) -> Finding:
    return Finding(
        type="unrequested_change",
        severity="medium",
        description=f"unrequested change in {file}",
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="code", ref=f"{file}#@@ -1 +1 @@")],
    )


def _case_a() -> BenchmarkCase:
    return BenchmarkCase(
        case_id="synthetic-a",
        source=BenchmarkCaseSource(kind="archetype", identifier="synthetic-a"),
        inputs=_inputs(),
        ground_truth=GroundTruthLabels(
            obligations=[
                GroundTruthObligation(
                    id="alpha",
                    description="Alpha",
                    explicit=True,
                    evidence_class="strongly_supported",
                    evidence_rationale="asserted",
                    candidate_tests=["T1"],
                ),
                GroundTruthObligation(
                    id="beta",
                    description="Beta",
                    explicit=True,
                    evidence_class="unsupported",
                    evidence_rationale="no test",
                    candidate_tests=[],
                ),
            ],
            gaps=[GroundTruthGap(id="gap-beta", description="Beta missing", obligation_id="beta")],
            unrequested_changes=[
                GroundTruthUnrequestedChange(
                    id="u-x", description="x.py changed", file="x.py", disposition="separable"
                )
            ],
        ),
        reviewer_output=Review(
            mode="local",
            reviewed_revision="def456",
            provenance=_provenance(),
            obligation_map=[_reviewer_obligation("Alpha", test_evidence=[])],
            findings=[_finding("Beta"), _unrequested_finding("x.py")],
        ),
    )


def _case_b() -> BenchmarkCase:
    return BenchmarkCase(
        case_id="synthetic-b",
        source=BenchmarkCaseSource(kind="archetype", identifier="synthetic-b"),
        inputs=_inputs(),
        ground_truth=GroundTruthLabels(
            obligations=[
                GroundTruthObligation(
                    id="gamma",
                    description="Gamma",
                    explicit=True,
                    evidence_class="strongly_supported",
                    evidence_rationale="asserted",
                    candidate_tests=["T2"],
                ),
            ],
            gaps=[],
        ),
        reviewer_output=Review(
            mode="local",
            reviewed_revision="def456",
            provenance=_provenance(),
            obligation_map=[
                _reviewer_obligation("Gamma", test_evidence=["T2"]),
                _reviewer_obligation("Delta", test_evidence=[]),
            ],
            findings=[_finding("Epsilon"), _unrequested_finding("y.py")],
        ),
    )


def test_pooled_report_matches_hand_calculated_values():
    report = score_case_set([_case_a(), _case_b()])

    assert report.case_count == 2
    assert report.determinism_mode == "replay"
    assert report.gap_recall == 1.0
    assert report.gap_precision == 0.5
    assert report.decomposition_accuracy == 2 / 3
    assert report.mapping_accuracy == 0.5
    assert report.evidence_agreement == 0.0
    assert report.unrequested_recall == 1.0
    assert report.unrequested_precision == 0.5


def test_report_includes_per_case_scores():
    report = score_case_set([_case_a(), _case_b()])

    assert len(report.per_case) == 2
    # Case A: gap 1/1, decomposition 1/2, mapping 0/1.
    assert report.per_case[0].gap_recall == 1.0
    assert report.per_case[0].gap_precision == 1.0
    assert report.per_case[0].decomposition_accuracy == 0.5
    assert report.per_case[0].mapping_accuracy == 0.0
    assert report.per_case[0].unrequested_recall == 1.0
    assert report.per_case[0].unrequested_precision == 1.0
    # Case B: no gaps -> recall None, precision 0/1; decomposition 1/2; mapping 1/1.
    assert report.per_case[1].gap_recall is None
    assert report.per_case[1].gap_precision == 0.0
    assert report.per_case[1].decomposition_accuracy == 1.0
    assert report.per_case[1].mapping_accuracy == 1.0
    # No unrequested-change ground truth in B -> recall None; the spurious
    # y.py finding still counts against precision (0/1).
    assert report.per_case[1].unrequested_recall is None
    assert report.per_case[1].unrequested_precision == 0.0


def test_empty_case_set_yields_no_metrics():
    report = score_case_set([])

    assert report.case_count == 0
    assert report.determinism_mode is None
    assert report.gap_recall is None
    assert report.gap_precision is None
    assert report.decomposition_accuracy is None
    assert report.mapping_accuracy is None
    assert report.evidence_agreement is None
    assert report.unrequested_precision is None
    assert report.unrequested_recall is None
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
