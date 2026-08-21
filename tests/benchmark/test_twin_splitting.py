"""Twin-splitting measurement over committed dogfood reports (#173).

These run against `dogfood-logs/`, which is committed, so they need no model
call and no transcript. The point of the measurement is that it stays
recomputable as new runs land.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from acceptance.benchmark.twin_splitting import (
    ReportMapping,
    TwinPair,
    by_band,
    collect,
    identical_only,
    parse_report,
    similarity,
    split_rate,
    twin_pairs,
)

REPO = Path(__file__).resolve().parents[2]
DOGFOOD = REPO / "dogfood-logs"


def _report(text: str, tmp_path: Path) -> ReportMapping:
    path = tmp_path / "output.log"
    path.write_text(text)
    return parse_report(path)


def test_a_reports_obligations_and_their_mapped_tests_are_read_back(tmp_path):
    parsed = _report(
        "Obligations:\n"
        "\n"
        "  1. The widget is green.\n"
        "       requirements: task-01\n"
        "       code evidence: addressed\n"
        "         1.1  src/widget.py#@@ -1,2 +1,3 @@\n"
        "       test evidence: strongly supported  [tier: static]\n"
        "         1.2  tests/test_widget.py::test_green\n"
        "\n"
        "  2. The widget is blue.\n"
        "       test evidence: unsupported\n",
        tmp_path,
    )
    assert parsed.obligations == {1: "The widget is green.", 2: "The widget is blue."}
    # The diff hunk under `code evidence` is not a test and must not be counted.
    assert parsed.mapped_tests == {1: ["tests/test_widget.py::test_green"], 2: []}


def test_a_test_mapped_to_only_one_of_two_identical_obligations_is_counted_as_split(tmp_path):
    parsed = _report(
        "  1. The widget is green.\n"
        "       test evidence: strongly supported\n"
        "         1.1  tests/test_widget.py::test_green\n"
        "         1.2  tests/test_widget.py::test_shared\n"
        "\n"
        "  2. The widget is green.\n"
        "       test evidence: strongly supported\n"
        "         2.1  tests/test_widget.py::test_shared\n",
        tmp_path,
    )
    (pair,) = twin_pairs(parsed)
    assert pair.identical is True
    assert pair.shared == 1  # test_shared reached both
    assert pair.split == 1  # test_green reached only the first
    assert split_rate([pair]) == 0.5


def test_split_rate_is_none_rather_than_zero_when_no_test_reached_either(tmp_path):
    parsed = _report(
        "  1. The widget is green.\n"
        "       test evidence: unsupported\n"
        "\n"
        "  2. The widget is green.\n"
        "       test evidence: unsupported\n",
        tmp_path,
    )
    assert split_rate(twin_pairs(parsed)) is None


def test_two_obligations_about_different_things_are_not_offered_as_a_pair(tmp_path):
    parsed = _report(
        "  1. The widget is green.\n"
        "       test evidence: strongly supported\n"
        "         1.1  tests/test_widget.py::test_green\n"
        "\n"
        "  2. Billing prorates a mid-cycle upgrade across the remaining days.\n"
        "       test evidence: strongly supported\n"
        "         2.1  tests/test_billing.py::test_prorates\n",
        tmp_path,
    )
    assert twin_pairs(parsed) == []


def test_similarity_ignores_wording_that_carries_no_signal():
    assert similarity("The widget is green.", "A widget that is green.") == 1.0
    assert similarity("The widget is green.", "The widget is blue.") < 1.0


def test_bands_keep_identical_text_apart_from_merely_similar_text():
    pairs = [
        TwinPair(
            source="s",
            left="x",
            right="x",
            similarity=1.0,
            identical=True,
            shared=1,
            split=0,
        ),
        TwinPair(
            source="s",
            left="x",
            right="y",
            similarity=0.75,
            identical=False,
            shared=0,
            split=3,
        ),
    ]
    grouped = by_band(pairs)
    assert [p.identical for p in grouped["identical"]] == [True]
    assert [p.similarity for p in grouped["0.70-0.79"]] == [0.75]
    # The identical pair must not also appear in a similarity band.
    assert all(not p.identical for name, ps in grouped.items() if name != "identical" for p in ps)


@pytest.mark.skipif(not DOGFOOD.is_dir(), reason="dogfood-logs/ not present")
def test_the_committed_dogfood_reports_still_yield_a_measurable_twin_population():
    """The measurement is only useful while it runs over the real corpus.

    Deliberately asserts the shape of the result, not a fixed rate — the rate
    moves as runs land, and pinning it would make every new dogfood run fail
    this test.
    """
    pairs = collect(sorted(DOGFOOD.glob("*/output.log")))
    assert len(pairs) > 20, "twin detection found almost nothing; the parser likely broke"
    assert any(p.opportunities for p in pairs), "no pair had a test reaching either side"
    rate = split_rate(pairs)
    assert rate is not None and 0.0 <= rate <= 1.0


@pytest.mark.skipif(not DOGFOOD.is_dir(), reason="dogfood-logs/ not present")
def test_identical_text_pairs_are_a_strict_subset_of_all_candidates():
    pairs = collect(sorted(DOGFOOD.glob("*/output.log")))
    assert len(identical_only(pairs)) <= len(pairs)
    assert all(p.left.strip() == p.right.strip() for p in identical_only(pairs))
