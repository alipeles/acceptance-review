"""Benchmark scoring & report (M-B0.3, §11.1).

Real scorer suite superseding M-B0.2's provisional score_case: gap-detection
recall, false-alarm precision, obligation-decomposition accuracy,
test-to-obligation mapping accuracy, and evidence-classification agreement.

Matching is exact-ref against the structured ground-truth refs from M-B0.1's
schema (GroundTruthGap.obligation_ref, GroundTruthMapping.test_id +
obligation_ref, etc.) against the corresponding fields on the reviewer's
Review — no fuzzy/NLP matching, since the ground-truth schema is already
structured rather than free text.

`evidence_agreement` is always computed with reported_total=0: Finding
(review_state.py) has no field for a §9.3 test-strength classification yet
— that's M5.3's job. M-B0.2's version compared Finding.evidence_tier (how
evidence was PRODUCED: builder-claim/static/coverage-confirmed/...) against
GroundTruthEvidenceClass.classification (how STRONG it is:
strongly_supported/unsupported/...) — two disjoint vocabularies that could
never usefully match. Being explicit that nothing is reported yet gives a
real, meaningful 0.0 ("the reviewer can't express this yet") rather than a
number that happens to read as zero for the wrong reason.

score_case and score_case_set pool the same per-case match counts; the case
set aggregates by pooling raw counts across all cases before dividing
(micro-averaging) rather than averaging each case's own ratio. That avoids
both macro- vs micro-averaging ambiguity and the awkwardness of averaging
in the presence of a per-case None (a case with no ground truth in a
category contributes no counts, rather than needing to be excluded from an
average). A macro-averaged variant (e.g. for per-source-type breakdowns) may
be worth adding later, but pooled counts stay the default so small or
no-op-heavy cases can't dilute the headline figures.

Variance disclosure (M-B0.4, §3.2's deferred "N-sample majority" alternative
to M0.5's fixed-seed strategy): every BenchmarkReport discloses its
determinism_mode (from the underlying cases' ReviewProvenance — kept as the
same plain string literal M0.5 used, independent of the LLM harness's Mode
enum). disclose_variance() then takes N such reports over repeated runs of
the same case set and computes a mean and spread per metric. It takes
already-computed reports rather than orchestrating the N runs itself: the
checker is still the M0.6 no-op skeleton, so there is no real variance yet
for a runner to produce — this function is ready the moment M1+ makes the
pipeline genuinely sampled, without speculative orchestration plumbing now.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field

from acceptance.benchmark.case import BenchmarkCase, BenchmarkScore
from acceptance.model_base import PersistableModel


@dataclass(frozen=True)
class _MatchCounts:
    matched: int
    ground_truth_total: int
    reported_total: int

    @staticmethod
    def zero() -> "_MatchCounts":
        return _MatchCounts(0, 0, 0)

    def __add__(self, other: "_MatchCounts") -> "_MatchCounts":
        return _MatchCounts(
            self.matched + other.matched,
            self.ground_truth_total + other.ground_truth_total,
            self.reported_total + other.reported_total,
        )

    def recall(self) -> float | None:
        if not self.ground_truth_total:
            return None
        return self.matched / self.ground_truth_total

    def precision(self) -> float | None:
        if not self.reported_total:
            return None
        return self.matched / self.reported_total


def _gap_counts(case: BenchmarkCase) -> _MatchCounts:
    review = case.reviewer_output
    ground_truth_refs = {g.obligation_ref for g in case.ground_truth.gaps if g.obligation_ref}
    reported_refs = {
        f.related_obligation for f in review.findings if f.related_obligation is not None
    }
    return _MatchCounts(
        matched=len(ground_truth_refs & reported_refs),
        ground_truth_total=len(ground_truth_refs),
        reported_total=len(reported_refs),
    )


def _decomposition_counts(case: BenchmarkCase) -> _MatchCounts:
    review = case.reviewer_output
    ground_truth_refs = {d.description for d in case.ground_truth.decomposition}
    reported_refs = {o.description for o in review.obligation_map}
    return _MatchCounts(
        matched=len(ground_truth_refs & reported_refs),
        ground_truth_total=len(ground_truth_refs),
        reported_total=len(reported_refs),
    )


def _mapping_counts(case: BenchmarkCase) -> _MatchCounts:
    review = case.reviewer_output
    ground_truth_refs = {(m.test_id, m.obligation_ref) for m in case.ground_truth.mappings}
    reported_refs = {
        (test_id, obligation.description)
        for obligation in review.obligation_map
        for test_id in obligation.test_evidence
    }
    return _MatchCounts(
        matched=len(ground_truth_refs & reported_refs),
        ground_truth_total=len(ground_truth_refs),
        reported_total=len(reported_refs),
    )


def _evidence_counts(case: BenchmarkCase) -> _MatchCounts:
    # reported_total is always 0: Finding has no §9.3 classification field
    # yet (M5.3). See module docstring — this is deliberate, not a stub.
    ground_truth_refs = {
        (e.obligation_ref, e.classification) for e in case.ground_truth.evidence_classes
    }
    return _MatchCounts(matched=0, ground_truth_total=len(ground_truth_refs), reported_total=0)


def _all_counts(case: BenchmarkCase) -> tuple[_MatchCounts, _MatchCounts, _MatchCounts, _MatchCounts]:
    if case.reviewer_output is None:
        raise ValueError(f"case {case.case_id!r} has no reviewer_output; run it first")
    return (
        _gap_counts(case),
        _decomposition_counts(case),
        _mapping_counts(case),
        _evidence_counts(case),
    )


def _score_from_counts(
    gap: _MatchCounts,
    decomposition: _MatchCounts,
    mapping: _MatchCounts,
    evidence: _MatchCounts,
) -> BenchmarkScore:
    return BenchmarkScore(
        gap_recall=gap.recall(),
        gap_precision=gap.precision(),
        decomposition_accuracy=decomposition.recall(),
        mapping_accuracy=mapping.recall(),
        evidence_agreement=evidence.recall(),
    )


def score_case(case: BenchmarkCase) -> BenchmarkScore:
    return _score_from_counts(*_all_counts(case))


class BenchmarkReport(PersistableModel):
    """Aggregate §11.1 metrics over a case set, pooled by raw match counts
    (micro-averaged) — the "single-command report over a case set"."""

    case_count: int
    determinism_mode: Literal["record", "replay"] | None = None
    gap_recall: float | None = None
    gap_precision: float | None = None
    decomposition_accuracy: float | None = None
    mapping_accuracy: float | None = None
    evidence_agreement: float | None = None
    per_case: list[BenchmarkScore] = Field(default_factory=list)


def _case_determinism_mode(case: BenchmarkCase) -> str:
    # reviewer_output is already known non-None here: _all_counts checks it
    # before this is called.
    provenance = case.reviewer_output.provenance
    if provenance is None:
        raise ValueError(
            f"case {case.case_id!r} has reviewer_output with no provenance; "
            "cannot disclose determinism mode"
        )
    return provenance.determinism_mode


def _reconcile_determinism_modes(modes: set[str]) -> str | None:
    if not modes:
        return None
    if len(modes) > 1:
        raise ValueError(f"case set mixes determinism modes: {sorted(modes)}")
    return next(iter(modes))


def score_case_set(cases: list[BenchmarkCase]) -> BenchmarkReport:
    gap_total = _MatchCounts.zero()
    decomposition_total = _MatchCounts.zero()
    mapping_total = _MatchCounts.zero()
    evidence_total = _MatchCounts.zero()
    per_case: list[BenchmarkScore] = []
    modes: set[str] = set()

    for case in cases:
        gap, decomposition, mapping, evidence = _all_counts(case)
        gap_total += gap
        decomposition_total += decomposition
        mapping_total += mapping
        evidence_total += evidence
        per_case.append(_score_from_counts(gap, decomposition, mapping, evidence))
        modes.add(_case_determinism_mode(case))

    return BenchmarkReport(
        case_count=len(cases),
        determinism_mode=_reconcile_determinism_modes(modes),
        gap_recall=gap_total.recall(),
        gap_precision=gap_total.precision(),
        decomposition_accuracy=decomposition_total.recall(),
        mapping_accuracy=mapping_total.recall(),
        evidence_agreement=evidence_total.recall(),
        per_case=per_case,
    )


_METRIC_FIELDS = (
    "gap_recall",
    "gap_precision",
    "decomposition_accuracy",
    "mapping_accuracy",
    "evidence_agreement",
)


class MetricStats(PersistableModel):
    mean: float | None = None
    # max - min across non-None samples; None if fewer than 2 contributed
    # (not enough samples to show variation — not a fabricated 0.0).
    spread: float | None = None


class SampledBenchmarkReport(PersistableModel):
    """N-run variance disclosure (M-B0.4): a mean and spread per §11.1
    metric across repeated runs of the same case set, plus each run's own
    report for traceability."""

    sample_count: int
    determinism_mode: Literal["record", "replay"]
    gap_recall: MetricStats
    gap_precision: MetricStats
    decomposition_accuracy: MetricStats
    mapping_accuracy: MetricStats
    evidence_agreement: MetricStats
    runs: list[BenchmarkReport] = Field(default_factory=list)


def _metric_stats(values: list[float | None]) -> MetricStats:
    present = [v for v in values if v is not None]
    if not present:
        return MetricStats(mean=None, spread=None)
    return MetricStats(
        mean=sum(present) / len(present),
        spread=(max(present) - min(present)) if len(present) >= 2 else None,
    )


def disclose_variance(reports: list[BenchmarkReport]) -> SampledBenchmarkReport:
    if not reports:
        raise ValueError("disclose_variance requires at least one report")

    modes = {r.determinism_mode for r in reports}
    if len(modes) > 1 or None in modes:
        raise ValueError(
            "reports must share a single known determinism mode, got "
            f"{sorted(m or 'unknown' for m in modes)}"
        )
    (mode,) = modes

    stats = {field: _metric_stats([getattr(r, field) for r in reports]) for field in _METRIC_FIELDS}

    return SampledBenchmarkReport(
        sample_count=len(reports),
        determinism_mode=mode,
        runs=reports,
        **stats,
    )
