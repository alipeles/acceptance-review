"""Benchmark scoring & report (M-B0.3, §11.1; ground-truth tree revised M-B5a.2;
unrequested-change axis added M3.5.1/DR-081).

The §11.1 metrics fall out of the obligation tree (case.py): decomposition
accuracy from the obligations, mapping accuracy from each obligation's
candidate_tests edges, evidence agreement from each obligation's evidence
class, and gap recall/precision from the gaps.

Unrequested-change precision/recall is a separate, obligation-*less* axis
(DR-081): a gap is an obligation with no matching code; an unrequested change
is code with no matching obligation. It is scored the same way (labeled refs
vs. reported refs, pooled by raw counts) but never folded into the gap
numbers — matching on the obligation-linked `related_obligation` field would
silently exclude every unrequested-change finding, which by construction
carries no obligation link at all.

Ground truth identifies obligations by a stable id; the reviewer's Review
(review_state.py) does not yet — its obligations are identified only by
description. So the cross-join to reviewer output is by description for now
(sharpened to semantic matching by #118's alignment, below); when M1 gives
reviewer obligations ids, these joins move to ids; the ground-truth tree is
already the anchor for that. Evidence agreement reads `Obligation.evidence_class`,
set by M5.3's strength classifier via `apply_evidence_strength` (M5.5); an
obligation the reviewer hasn't classified yet contributes no reported ref.

Aggregation pools raw match counts across cases before dividing
(micro-averaging), so small or no-op-heavy cases can't dilute the headline
figures; a macro-averaged variant may be added later. A ratio is None when
undefined (no ground truth, or nothing reported) rather than a misleading 0.0.

Semantic matching (#118): the obligation-keyed joins (gap, decomposition,
mapping) match reviewer criteria to ground truth by description. Pass a
`client` to score_case/score_case_set and an LLM aligns semantically-equivalent
criteria first (alignment.py), so a correct-but-reworded criterion counts as
matched; the reviewer-side descriptions are remapped through that alignment
before the set intersection. With no client the alignment is empty — identity
remap, i.e. exact-string match, the original behavior — so hand-aligned fixtures
score unchanged.

Variance disclosure: every BenchmarkReport discloses its determinism_mode
(from the cases' ReviewProvenance); disclose_variance() computes a mean and
spread per metric across N runs of the same case set.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field

from acceptance.benchmark.alignment import align_obligations
from acceptance.benchmark.case import BenchmarkCase, BenchmarkScore
from acceptance.llm import ModelClient
from acceptance.model_base import PersistableModel
from acceptance.review_state import UNREQUESTED_CHANGE


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


def _counts(ground_truth_refs: set, reported_refs: set) -> _MatchCounts:
    return _MatchCounts(
        matched=len(ground_truth_refs & reported_refs),
        ground_truth_total=len(ground_truth_refs),
        reported_total=len(reported_refs),
    )


def _remap(description: str, alignment: dict[str, str]) -> str:
    """Reviewer description -> its aligned ground-truth description (or itself
    if unmatched / no alignment). Empty alignment = identity = exact match."""
    return alignment.get(description, description)


def _gap_counts(case: BenchmarkCase, alignment: dict[str, str]) -> _MatchCounts:
    review = case.reviewer_output
    obligation_desc = {o.id: o.description for o in case.ground_truth.obligations}
    # A gap is keyed by the obligation it concerns (so "found" means the checker
    # flagged a finding for that obligation); an obligation-less gap (e.g. a
    # declaration overclaim) is keyed by its own id and is unmatchable until the
    # declaration-comparison capability (M6) can produce it.
    ground_truth_refs = {
        obligation_desc.get(gap.obligation_id, gap.id) for gap in case.ground_truth.gaps
    }
    reported_refs = {
        _remap(f.related_obligation, alignment)
        for f in review.findings
        if f.related_obligation is not None
    }
    return _counts(ground_truth_refs, reported_refs)


def _unrequested_counts(case: BenchmarkCase) -> _MatchCounts:
    """Code→obligation axis (DR-081): matched by file, not by obligation —
    an unrequested-change finding never carries `related_obligation` (§9.2,
    obligation-less by construction), so this never routes through any
    obligation's coverage classification."""
    review = case.reviewer_output
    ground_truth_refs = {u.file for u in case.ground_truth.unrequested_changes}
    reported_refs = {
        link.ref.split("#", 1)[0]
        for finding in review.findings
        if finding.type == UNREQUESTED_CHANGE
        for link in finding.links
        if link.kind == "code"
    }
    return _counts(ground_truth_refs, reported_refs)


def _decomposition_counts(case: BenchmarkCase, alignment: dict[str, str]) -> _MatchCounts:
    review = case.reviewer_output
    ground_truth_refs = {o.description for o in case.ground_truth.obligations}
    reported_refs = {_remap(o.description, alignment) for o in review.obligation_map}
    return _counts(ground_truth_refs, reported_refs)


def _mapping_counts(case: BenchmarkCase, alignment: dict[str, str]) -> _MatchCounts:
    review = case.reviewer_output
    ground_truth_refs = {
        (obligation.description, test_id)
        for obligation in case.ground_truth.obligations
        for test_id in obligation.candidate_tests
    }
    reported_refs = {
        (_remap(obligation.description, alignment), test_id)
        for obligation in review.obligation_map
        for test_id in obligation.test_evidence
    }
    return _counts(ground_truth_refs, reported_refs)


def _evidence_counts(case: BenchmarkCase, alignment: dict[str, str]) -> _MatchCounts:
    # Every obligation carries an evidence class, so the denominator is the full
    # decomposition. A reviewer Obligation expresses its §9.3 classification via
    # `evidence_class` (M5.3/M5.5); one with none set (not yet classified)
    # contributes no reported ref, same as any other unreported obligation.
    review = case.reviewer_output
    ground_truth_refs = {
        (obligation.description, obligation.evidence_class)
        for obligation in case.ground_truth.obligations
    }
    reported_refs = {
        (_remap(obligation.description, alignment), obligation.evidence_class)
        for obligation in review.obligation_map
        if obligation.evidence_class is not None
    }
    return _counts(ground_truth_refs, reported_refs)


def _alignment(case: BenchmarkCase, client: ModelClient | None) -> dict[str, str]:
    """Reviewer->ground-truth description remap for this case. Empty (identity /
    exact match) when no client is given; an LLM semantic alignment otherwise."""
    if client is None:
        return {}
    return align_obligations(
        [o.description for o in case.ground_truth.obligations],
        [o.description for o in case.reviewer_output.obligation_map],
        client,
    )


def _all_counts(
    case: BenchmarkCase, client: ModelClient | None = None
) -> tuple[_MatchCounts, _MatchCounts, _MatchCounts, _MatchCounts, _MatchCounts]:
    if case.reviewer_output is None:
        raise ValueError(f"case {case.case_id!r} has no reviewer_output; run it first")
    alignment = _alignment(case, client)
    return (
        _gap_counts(case, alignment),
        _decomposition_counts(case, alignment),
        _mapping_counts(case, alignment),
        _evidence_counts(case, alignment),
        _unrequested_counts(case),
    )


def _score_from_counts(
    gap: _MatchCounts,
    decomposition: _MatchCounts,
    mapping: _MatchCounts,
    evidence: _MatchCounts,
    unrequested: _MatchCounts,
) -> BenchmarkScore:
    return BenchmarkScore(
        gap_recall=gap.recall(),
        gap_precision=gap.precision(),
        decomposition_accuracy=decomposition.recall(),
        mapping_accuracy=mapping.recall(),
        evidence_agreement=evidence.recall(),
        unrequested_precision=unrequested.precision(),
        unrequested_recall=unrequested.recall(),
    )


def score_case(case: BenchmarkCase, client: ModelClient | None = None) -> BenchmarkScore:
    """Score one case. Pass a `client` for semantic obligation matching (#118);
    with none, the obligation-keyed metrics fall back to exact-string match."""
    return _score_from_counts(*_all_counts(case, client))


class BenchmarkReport(PersistableModel):
    """Aggregate §11.1 metrics over a case set, pooled by raw match counts
    (micro-averaged) — the "single-command report over a case set"."""

    case_count: int
    determinism_mode: Literal["record", "replay"] | None = None
    gap_recall: float | None = None
    gap_precision: float | None = None
    decomposition_accuracy: float | None = None
    # NOT COMPARABLE ACROSS #164. The mapping stage now partitions its request
    # across several calls instead of asking one call for every test-obligation
    # judgment (DR-164), which changes the prompts and forced the whole mapping
    # transcript corpus to be re-recorded. A mapping-accuracy figure from before
    # that change and one from after measure different questions being asked, so
    # they must not be plotted as a trend or cited as a regression/improvement.
    mapping_accuracy: float | None = None
    evidence_agreement: float | None = None
    unrequested_precision: float | None = None
    unrequested_recall: float | None = None
    per_case: list[BenchmarkScore] = Field(default_factory=list)


def _case_determinism_mode(case: BenchmarkCase) -> str:
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


def score_case_set(
    cases: list[BenchmarkCase], client: ModelClient | None = None
) -> BenchmarkReport:
    gap_total = _MatchCounts.zero()
    decomposition_total = _MatchCounts.zero()
    mapping_total = _MatchCounts.zero()
    evidence_total = _MatchCounts.zero()
    unrequested_total = _MatchCounts.zero()
    per_case: list[BenchmarkScore] = []
    modes: set[str] = set()

    for case in cases:
        gap, decomposition, mapping, evidence, unrequested = _all_counts(case, client)
        gap_total += gap
        decomposition_total += decomposition
        mapping_total += mapping
        evidence_total += evidence
        unrequested_total += unrequested
        per_case.append(_score_from_counts(gap, decomposition, mapping, evidence, unrequested))
        modes.add(_case_determinism_mode(case))

    return BenchmarkReport(
        case_count=len(cases),
        determinism_mode=_reconcile_determinism_modes(modes),
        gap_recall=gap_total.recall(),
        gap_precision=gap_total.precision(),
        decomposition_accuracy=decomposition_total.recall(),
        mapping_accuracy=mapping_total.recall(),
        evidence_agreement=evidence_total.recall(),
        unrequested_precision=unrequested_total.precision(),
        unrequested_recall=unrequested_total.recall(),
        per_case=per_case,
    )


_METRIC_FIELDS = (
    "gap_recall",
    "gap_precision",
    "decomposition_accuracy",
    "mapping_accuracy",
    "evidence_agreement",
    "unrequested_precision",
    "unrequested_recall",
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
    # Not comparable across #164 — see BenchmarkReport.mapping_accuracy. Spread
    # pooled across that boundary would read as model variance when it is the
    # partitioning change.
    mapping_accuracy: MetricStats
    evidence_agreement: MetricStats
    unrequested_precision: MetricStats
    unrequested_recall: MetricStats
    runs: list[BenchmarkReport] = Field(default_factory=list)


def metric_stats(values: list[float | None]) -> MetricStats:
    """Mean and spread over the present samples.

    Public because the instability harness (#189) measures over its own figures
    and must not grow a second variance path — the constraint is that statistics
    come from here, and a private helper would have forced a copy.
    """
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

    stats = {field: metric_stats([getattr(r, field) for r in reports]) for field in _METRIC_FIELDS}

    return SampledBenchmarkReport(
        sample_count=len(reports),
        determinism_mode=mode,
        runs=reports,
        **stats,
    )
