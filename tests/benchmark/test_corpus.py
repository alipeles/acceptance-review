"""#190: the rating-stability corpus as materializable benchmark cases.

These cases are pinned to real commits in this repository rather than to
hand-built fixture trees, so the materializer's job is different from
`fixtures.py`'s: nothing is copied, and the thing that can go wrong is the
history moving underneath it.
"""

import json
from pathlib import Path

import pytest

from acceptance.benchmark.corpus import (
    UnresolvableRevisionError,
    build_corpus_case,
    resolve_case_revisions,
    load_corpus_meta,
    materialize_corpus_run,
    remove_corpus_worktree,
)

REPO = Path(__file__).resolve().parents[2]
CASES_DIR = REPO / "tests" / "fixtures" / "rating-regression"
CORPUS_DIR = REPO / "tests" / "fixtures" / "rating-stability"

CASE_DIRS = sorted(p for p in CASES_DIR.iterdir() if p.is_dir())


@pytest.fixture
def worktree(tmp_path):
    """Materialize into tmp_path, and always deregister the worktree.

    Registration lives in the main repository's `.git`, so a test that only
    deleted its tmp_path would leave this repo accumulating stale entries.
    """
    dest = tmp_path / "worktree"
    yield dest
    remove_corpus_worktree(REPO, dest)


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=lambda p: p.name)
def test_every_case_names_a_revision_this_repository_still_has(case_dir):
    """The suite is pinned to real history. If a rebase ever orphans one of
    these commits, this fails by name — the case cannot quietly disappear."""
    meta = load_corpus_meta(case_dir)
    base, head = resolve_case_revisions(case_dir, REPO)
    assert base.startswith(meta.base_revision)
    assert head.startswith(meta.head_revision)


def test_a_revision_that_no_longer_resolves_fails_by_name(tmp_path):
    """The failure mode that matters: a suite pinned to history must break
    loudly when the history moves, never shrink silently."""
    case_dir = tmp_path / "999-gate2-run1"
    case_dir.mkdir()
    (case_dir / "case.json").write_text(
        json.dumps(
            {
                "corpus_run": "999-gate2-run1",
                "base_revision": "839ea47",
                "head_revision": "0" * 40,
                "judgement": "n/a",
                "summary": "n/a",
            }
        )
    )

    with pytest.raises(UnresolvableRevisionError) as excinfo:
        materialize_corpus_run(case_dir, REPO, tmp_path / "wt")

    assert "999-gate2-run1" in str(excinfo.value)


def test_the_worktree_holds_the_tree_as_it_was_not_as_it_is(worktree):
    """The reason a worktree exists at all.

    `evidence/discovery.py` scans the filesystem for `test_*.py`, not the git
    revision, so a case pointed at the live repo would discover today's tests
    against a historical diff. The check is a file this repository has now and
    did not have at the case's head revision.
    """
    case_dir = CASES_DIR / "167-gate2-run3"
    run = materialize_corpus_run(case_dir, REPO, worktree)

    assert (run.worktree / "tests" / "test_cli.py").is_file()
    # Added well after 95b880a — its presence would mean we were looking at the
    # working tree rather than the revision under review.
    assert not (run.worktree / "src" / "acceptance" / "benchmark" / "corpus.py").exists()
    assert (REPO / "src" / "acceptance" / "benchmark" / "corpus.py").is_file()


def test_the_case_carries_the_task_file_the_run_was_actually_given(worktree):
    case_dir = CASES_DIR / "167-gate2-run3"
    case = build_corpus_case(case_dir, REPO, CORPUS_DIR, worktree)

    corpus_task = (CORPUS_DIR / "167-gate2-run3" / "current-task.md").read_text()
    assert case.inputs.task_text == corpus_task
    # Read from the corpus, never copied into the case directory — a second
    # copy could drift from the evidence record.
    assert not (case_dir / "current-task.md").exists()


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=lambda p: p.name)
def test_every_case_is_traceable_to_the_judgement_it_came_from(case_dir):
    meta = load_corpus_meta(case_dir)
    judgement = CORPUS_DIR / meta.corpus_run / "judgement.md"
    assert judgement.is_file()
    assert meta.corpus_run in meta.judgement or "judgement.md" in meta.judgement


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=lambda p: p.name)
def test_every_case_names_a_corpus_run_that_exists(case_dir):
    meta = load_corpus_meta(case_dir)
    run = CORPUS_DIR / meta.corpus_run
    assert (run / "current-task.md").is_file()
    assert (run / "check-output.log").is_file()


# The both-directions property is asserted over the case SET in
# `test_rating_regression.py`, not per case. Two cases — `167-gate2-run5` and
# the `163-gate2-run1` control — are legitimately all-strong, so a per-case
# version would have forced a label the corpus does not support.
