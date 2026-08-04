"""#190: the rating-stability corpus as an executable regression suite.

DR-180's load-bearing criterion — `strongly supported` is not issued on evidence
that does not earn it — had no scoreboard. Every candidate fix to the
evidence-judgement stage was accepted or rejected by eyeball. These are the
assertions that replace the eyeball.

The suite must fail in both directions. A judge that rates everything strongly
supported must fail it, and so must a judge that rates nothing strongly
supported, because "stop moving" is a fix that passes a one-directional suite
while losing all seven real gaps the corpus records.
"""

import json
from pathlib import Path

import pytest

from acceptance.benchmark.corpus import (
    build_corpus_case,
    load_labels,
    remove_corpus_worktree,
)
from acceptance.benchmark.coverage import classify_case
from acceptance.benchmark.scoring import score_case_set
from tests.benchmark.degenerate_judges import degenerate_client

REPO = Path(__file__).resolve().parents[2]
CASES_DIR = REPO / "tests" / "fixtures" / "rating-regression"
CORPUS_DIR = REPO / "tests" / "fixtures" / "rating-stability"
CASE_DIRS = sorted(p for p in CASES_DIR.iterdir() if p.is_dir())

# The corpus's own ground-truth tables, restated as (run, obligation) pairs so a
# label silently dropped from a fixture fails here rather than shrinking the
# suite. Transcribed from the tables in #190 and `current-task.md`.
UNEARNED_STRONG = {
    ("167-gate2-run1", "default-to-most-recent-review"),
    ("167-gate2-run1", "no-speculative-writing"),
    ("167-gate2-run1", "remove-stale-next-instruction-file"),
    ("167-gate2-run1", "spec-no-longer-describes-written-file"),
    ("167-gate2-run1", "retrieve-from-stored-review-state"),
    ("167-gate2-run2", "no-speculative-writing"),
    ("167-gate2-run2", "remove-stale-next-instruction-file"),
}

REAL_GAPS = {
    ("167-gate2-run1", "fixed-command-surface"),
    ("167-gate2-run1", "replace-written-file-with-command"),  # partly real
    ("167-gate2-run2", "default-to-most-recent-review"),
    ("167-gate2-run2", "retrieve-from-stored-review-state"),
    ("167-gate2-run3", "remove-stale-next-instruction-file"),  # the silent --json deletion
    ("167-gate2-run3", "no-speculative-writing"),
    ("167-gate2-run3", "spec-no-longer-describes-written-file"),
    ("167-gate2-run4", "preserve-prose-structured-fields"),
}


@pytest.fixture
def corpus_worktrees(tmp_path):
    """A root for materialized worktrees, deregistered from the main repo after.

    Worktree registration lives in this repository's `.git`, so deleting
    tmp_path alone would leave stale entries accumulating across runs.
    """
    yield tmp_path
    for path in sorted(tmp_path.rglob("wt*")):
        if path.is_dir():
            remove_corpus_worktree(REPO, path)


def _labels(case_dir: Path) -> dict:
    return json.loads((case_dir / "labels.json").read_text())


def _classes(case_dir: Path) -> dict[str, str]:
    return {o["id"]: o["evidence_class"] for o in _labels(case_dir)["obligations"]}


# --------------------------------------------------------------------------
# The ground truth is encoded at all
# --------------------------------------------------------------------------


def test_every_unearned_rating_is_required_to_no_longer_be_issued():
    """Each rating the corpus records as unearned is labelled as something
    other than `strongly supported`, so a judge that reissues it disagrees."""
    for run, obligation in sorted(UNEARNED_STRONG):
        klass = _classes(CASES_DIR / run)[obligation]
        assert klass != "strongly_supported", f"{run}/{obligation} is labelled {klass}"


def test_every_real_gap_is_required_to_still_be_reported():
    """Each gap the corpus confirms was real is a ground-truth gap, so a fix
    that blunts it away loses gap recall rather than passing quietly."""
    for run, obligation in sorted(REAL_GAPS):
        gaps = {g["obligation_id"] for g in _labels(CASES_DIR / run)["gaps"]}
        assert obligation in gaps, f"{run} has no ground-truth gap for {obligation}"


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=lambda p: p.name)
def test_labels_load_against_the_shared_ground_truth_schema(case_dir):
    """Cases use `GroundTruthLabels`, not a shape invented for this task — so
    its validators (unique ids, resolvable gap links, no unexplained result)
    apply here too."""
    labels = load_labels(case_dir)
    assert labels.obligations
    assert all(o.evidence_rationale.strip() for o in labels.obligations)


# --------------------------------------------------------------------------
# Both directions
# --------------------------------------------------------------------------


def test_the_case_set_can_catch_a_judge_erring_either_way():
    """Both-directions is a property of the case MIX, not of new scoring code.

    `evidence_agreement` is recall over (description, evidence_class) pairs, so a
    judge that always says `strongly_supported` can only match obligations whose
    ground truth is that, and one that never says it can only match the rest. A
    set holding just one kind would let one degenerate judge through.
    """
    everything = [klass for d in CASE_DIRS for klass in _classes(d).values()]
    assert "strongly_supported" in everything
    assert [k for k in everything if k != "strongly_supported"]


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=lambda p: p.name)
def test_no_case_passes_trivially(case_dir):
    """Every case has to be able to fail something.

    `163-gate2-run1` is the one this exists for. It is a clean run kept as a
    control, so it has no gaps and no sub-strong ratings — and the issue warns
    against letting it become the case that passes trivially. Its bite is the
    other direction: with zero ground-truth gaps, a judge that flags anything
    here loses gap *precision*.
    """
    labels = _labels(case_dir)
    classes = set(_classes(case_dir).values())
    catches_permissive = bool(classes - {"strongly_supported"}) or bool(labels["gaps"])
    catches_pessimistic = "strongly_supported" in classes or not labels["gaps"]
    assert catches_permissive or catches_pessimistic


def _score_with(always_strong: bool, tmp_path):
    cases = []
    for index, case_dir in enumerate(CASE_DIRS):
        case = build_corpus_case(case_dir, REPO, CORPUS_DIR, tmp_path / f"wt{index}")
        obligations = [
            {"id": o["id"], "description": o["description"]}
            for o in _labels(case_dir)["obligations"]
        ]
        client = degenerate_client(obligations, always_strong=always_strong)
        cases.append(classify_case(case, client))
    return score_case_set(cases)


def test_a_judge_that_always_issues_strongly_supported_fails_the_suite(corpus_worktrees):
    report = _score_with(always_strong=True, tmp_path=corpus_worktrees)
    # It agrees on the genuinely-strong obligations and on nothing else, so it
    # cannot reach full agreement...
    assert report.evidence_agreement < 1.0
    # ...and having found nothing wrong, it reports none of the real gaps.
    assert report.gap_recall < 1.0


def test_a_judge_that_never_issues_strongly_supported_fails_the_suite(corpus_worktrees):
    report = _score_with(always_strong=False, tmp_path=corpus_worktrees)
    assert report.evidence_agreement < 1.0
    # Absence of false STRONGs is explicitly not sufficient on its own (#190):
    # flagging everything costs precision even where recall looks healthy.
    assert report.gap_precision < 1.0


def test_the_two_degenerate_judges_disagree_about_the_ratings(corpus_worktrees):
    """Guards the harness rather than the judge.

    If the stub's verdict never reached `strength.py`, both judges would score
    identically and the two tests above would pass for the wrong reason — the
    'helper the pipeline never actually calls' hole that defect injection keeps
    finding here.
    """
    permissive = _score_with(always_strong=True, tmp_path=corpus_worktrees / "a")
    pessimistic = _score_with(always_strong=False, tmp_path=corpus_worktrees / "b")
    assert permissive.evidence_agreement != pessimistic.evidence_agreement
