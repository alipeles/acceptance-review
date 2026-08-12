"""M1.4 acceptance: archetype cases report a decomposition-accuracy number.

decompose_case only needs a case's task text (no repo materialization), so
these tests inject a recorded model response directly — replay-first, no live
calls, same pattern as M1.2/M1.3's tests.
"""

from pathlib import Path

from acceptance.benchmark.decomposition import decompose_case
from acceptance.benchmark.fixtures import build_benchmark_case
from acceptance.benchmark.scoring import score_case_set
from tests.support import client_returning as _client_returning

ARCHETYPES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"
FIXTURE_DIRS = sorted(p for p in ARCHETYPES_DIR.iterdir() if p.is_dir())


def _obligation_response(descriptions: list[str]) -> dict:
    return {
        "obligations": [
            {
                "id": f"o{i}",
                "description": desc,
                "type": "functional",
                "importance": "normal",
                "explicit": True,
                "observable_behavior": "...",
                "source_quote": desc,
            }
            for i, desc in enumerate(descriptions)
        ],
        "open_questions": [],
        "requirement_dispositions": [],
    }


def test_archetype_1_reports_the_expected_decomposition_accuracy(tmp_path):
    """The real archetype #1 ground truth has 4 obligations; a decomposition
    that reproduces 3 of the 4 exact descriptions (omitting the returns-in-
    parens obligation, matching the archetype's own missed-obligation story)
    yields decomposition_accuracy == 3/4."""
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    response = _obligation_response(
        [
            "Show the item name, quantity, and unit price",
            "Include the line total (quantity times unit price)",
            "Format money as USD with two decimals and a leading $",
        ]
    )

    scored = decompose_case(case, _client_returning(response))

    assert scored.score is not None
    assert scored.score.decomposition_accuracy == 3 / 4


def test_decompose_case_does_not_mutate_the_input_case(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    decompose_case(case, _client_returning(_obligation_response([])))

    assert case.reviewer_output is None
    assert case.score is None


def test_all_archetype_cases_report_a_decomposition_accuracy_number(tmp_path):
    """Pooled across all nine archetypes: score_case_set reports a real,
    non-None decomposition_accuracy — the M1.4 acceptance."""
    scored_cases = []
    for i, fixture_dir in enumerate(FIXTURE_DIRS):
        case = build_benchmark_case(fixture_dir, tmp_path / f"repo-{i}")
        # Synthetic response: every ground-truth obligation but the last one,
        # reusing the case's own labels (no hand-typed descriptions needed).
        descriptions = [o.description for o in case.ground_truth.obligations]
        response = _obligation_response(descriptions[:-1] if len(descriptions) > 1 else [])
        scored_cases.append(decompose_case(case, _client_returning(response)))

    report = score_case_set(scored_cases)

    assert report.case_count == len(FIXTURE_DIRS)
    assert report.decomposition_accuracy is not None
    assert 0.0 < report.decomposition_accuracy < 1.0
    # Every individual archetype case also reports its own number.
    for case_score in report.per_case:
        assert case_score.decomposition_accuracy is not None


def test_decompose_case_leaves_other_metrics_as_no_op_defaults(tmp_path):
    """Only decomposition_accuracy is meaningful here; gaps/mappings/evidence
    are untouched since decompose_case doesn't populate findings."""
    case = build_benchmark_case(ARCHETYPES_DIR / "09-revision-cycle", tmp_path / "repo")
    scored = decompose_case(case, _client_returning(_obligation_response([])))

    assert scored.score.gap_recall is None  # archetype 09 has no ground-truth gaps
    assert scored.score.mapping_accuracy == 0.0  # ground truth has mappings; none reported
