"""The ranking experiment's findings record what #348 rests on.

Two things #348 asked to be written down: whether the similarity ranking still
holds with the embedding request the review can actually send (no `input_type`),
and what stopping early costs and saves when replayed over recorded reviews.

Narrow, like `test_decision_records.py`: these check that each outcome is
stated, and that the replay figures in the prose are the ones the committed
replay logs printed — so the findings cannot drift from the measurement they
report.
"""

from __future__ import annotations

import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parents[1] / "docs" / "experiments" / "rank-prefilter"
FINDINGS = HERE / "FINDINGS.md"


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_the_findings_record_that_the_ranking_holds_without_input_type():
    flat = _flat(FINDINGS.read_text())

    assert "The ranking holds without Voyage's `input_type`" in flat
    assert "`build_embedding_request` stays untouched" in flat


def test_the_findings_record_the_embedding_model_the_review_ranks_with():
    flat = _flat(FINDINGS.read_text())

    assert "#348 ranks with the configured embedding model" in flat


def _replayed(log: str) -> tuple[str, str, str]:
    """(criteria that differ, criteria total, share of pairs asked) from a log."""
    text = (HERE / log).read_text()
    criteria = re.search(r"criteria: (\d+); .* differ on (\d+)", text)
    share = re.search(r"the walk asked \d+ \(([\d.]+%)\)", text)
    assert criteria and share, f"{log} does not carry the replay summary"
    return criteria.group(2), criteria.group(1), share.group(1)


def test_the_replay_figures_in_the_findings_are_the_ones_the_replay_printed():
    flat = _flat(FINDINGS.read_text())

    for log, review in (("replay-340.log", "#340"), ("replay-45-run3.log", "#45 run 3")):
        differ, total, share = _replayed(log)
        assert differ == "0", f"{review}: the replay found ratings that differ"
        assert f"{differ} of {total}" in flat, f"{review}: criteria count not in the findings"
        assert share in flat, f"{review}: share of pairs asked not in the findings"


def test_the_findings_record_what_stopping_early_costs_per_covered_defect():
    """The median is the bar #348 settled on; the mean is reported beside it."""
    flat = _flat(FINDINGS.read_text())

    for log in ("replay-340.log", "replay-45-run3.log"):
        text = (HERE / log).read_text()
        median = re.search(r"judgements per covered defect: median (\d+)", text).group(1)
        mean = re.search(r"mean ([\d.]+) judgements per covered defect", text).group(1)
        assert f"{mean} / {median}" in flat, f"{log}: mean / median not in the findings"
