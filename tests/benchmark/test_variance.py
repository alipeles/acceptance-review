"""M-B0.4 acceptance: report output includes the determinism mode and (when
sampled) a spread figure per metric.

disclose_variance() takes already-computed BenchmarkReports rather than
running anything itself — the pipeline is still the M0.6 no-op skeleton, so
there's no real sampled variance to produce yet. These reports stand in for
three repetitions of the same case set under a live/sampled configuration.

gap_recall across 3 runs: 0.5, 0.6, 0.7 -> mean = 0.6, spread = 0.7-0.5 = 0.2
gap_precision: 0.4, 0.4, 0.4            -> mean = 0.4, spread = 0.0
decomposition_accuracy: None, 0.5, 0.5  -> only 2 contribute: mean = 0.5, spread = 0.0
mapping_accuracy: always None            -> mean = None, spread = None
evidence_agreement: 0.0 (single value)   -> not used here; covered separately
"""

import pytest

from acceptance.benchmark.scoring import BenchmarkReport, disclose_variance


def _report(**metrics) -> BenchmarkReport:
    return BenchmarkReport(case_count=2, determinism_mode="record", **metrics)


def test_disclose_variance_matches_hand_calculated_values():
    reports = [
        _report(gap_recall=0.5, gap_precision=0.4, decomposition_accuracy=None),
        _report(gap_recall=0.6, gap_precision=0.4, decomposition_accuracy=0.5),
        _report(gap_recall=0.7, gap_precision=0.4, decomposition_accuracy=0.5),
    ]

    disclosure = disclose_variance(reports)

    assert disclosure.sample_count == 3
    assert disclosure.determinism_mode == "record"

    assert disclosure.gap_recall.mean == pytest.approx(0.6)
    assert disclosure.gap_recall.spread == pytest.approx(0.2)

    assert disclosure.gap_precision.mean == pytest.approx(0.4)
    assert disclosure.gap_precision.spread == pytest.approx(0.0)

    # Only 2 of 3 runs reported a value; the None is excluded, not treated as 0.
    assert disclosure.decomposition_accuracy.mean == pytest.approx(0.5)
    assert disclosure.decomposition_accuracy.spread == pytest.approx(0.0)

    # Never reported in any run: no mean, no spread.
    assert disclosure.mapping_accuracy.mean is None
    assert disclosure.mapping_accuracy.spread is None

    assert disclosure.runs == reports


def test_a_metric_present_in_only_one_run_has_no_spread():
    reports = [_report(evidence_agreement=0.3), _report(evidence_agreement=None)]

    disclosure = disclose_variance(reports)

    # Not enough samples to show variation: undefined, not a fabricated 0.0.
    assert disclosure.evidence_agreement.mean == pytest.approx(0.3)
    assert disclosure.evidence_agreement.spread is None


def test_single_report_disclosure_has_no_spread_anywhere():
    disclosure = disclose_variance([_report(gap_recall=0.6, gap_precision=1.0)])

    assert disclosure.sample_count == 1
    assert disclosure.gap_recall.mean == pytest.approx(0.6)
    assert disclosure.gap_recall.spread is None
    assert disclosure.gap_precision.spread is None


def test_disclose_variance_requires_at_least_one_report():
    with pytest.raises(ValueError):
        disclose_variance([])


def test_disclose_variance_rejects_mixed_determinism_modes():
    reports = [
        _report(gap_recall=0.5),
        BenchmarkReport(case_count=2, determinism_mode="replay", gap_recall=0.6),
    ]
    with pytest.raises(ValueError):
        disclose_variance(reports)


def test_disclose_variance_rejects_reports_with_unknown_mode():
    reports = [_report(gap_recall=0.5), BenchmarkReport(case_count=2, gap_recall=0.6)]
    with pytest.raises(ValueError):
        disclose_variance(reports)
