"""Minimal per-case scoring (M-B0.2).

This is deliberately narrow: just enough to satisfy M-B0.2's own acceptance
check ("running the empty skeleton over an archetype case yields a scored
(all-miss) result"). It counts exact ref matches between a case's ground
truth and its reviewer_output. M-B0.3 owns the real rubric — matching
semantics beyond exact refs, aggregation into a report across a case set,
and false-alarm/agreement scoring nuance — and supersedes this module rather
than building alongside it.

A ratio is `None` when it is mathematically undefined rather than a
misleading 0.0 or 1.0: precision with zero reported findings, or evidence
agreement with zero reported classifications, has nothing to be right or
wrong about.
"""

from __future__ import annotations

from acceptance.benchmark.case import BenchmarkCase, BenchmarkScore


def score_case(case: BenchmarkCase) -> BenchmarkScore:
    review = case.reviewer_output
    if review is None:
        raise ValueError("cannot score a case with no reviewer_output")
    gt = case.ground_truth

    reported_gap_refs = {
        f.related_obligation for f in review.findings if f.related_obligation is not None
    }
    reported_obligation_refs = {o.description for o in review.obligation_map}
    reported_mapping_refs = {
        (t, o) for o in review.obligation_map for t in o.test_evidence
    }
    reported_evidence_refs = {
        (f.related_obligation, f.evidence_tier.name)
        for f in review.findings
        if f.related_obligation is not None
    }

    return BenchmarkScore(
        gap_recall=_recall(
            ground_truth_refs={g.obligation_ref for g in gt.gaps if g.obligation_ref},
            reported_refs=reported_gap_refs,
        ),
        gap_precision=_precision(
            ground_truth_refs={g.obligation_ref for g in gt.gaps if g.obligation_ref},
            reported_refs=reported_gap_refs,
        ),
        decomposition_accuracy=_recall(
            ground_truth_refs={d.description for d in gt.decomposition},
            reported_refs=reported_obligation_refs,
        ),
        mapping_accuracy=_recall(
            ground_truth_refs={(m.test_id, m.obligation_ref) for m in gt.mappings},
            reported_refs=reported_mapping_refs,
        ),
        evidence_agreement=_precision(
            ground_truth_refs={
                (e.obligation_ref, e.classification) for e in gt.evidence_classes
            },
            reported_refs=reported_evidence_refs,
        ),
    )


def _recall(ground_truth_refs: set, reported_refs: set) -> float | None:
    """Of the known ground-truth items, how many were reported?"""
    if not ground_truth_refs:
        return None
    return len(ground_truth_refs & reported_refs) / len(ground_truth_refs)


def _precision(ground_truth_refs: set, reported_refs: set) -> float | None:
    """Of the reported items, how many were actually in ground truth?"""
    if not reported_refs:
        return None
    return len(ground_truth_refs & reported_refs) / len(reported_refs)
