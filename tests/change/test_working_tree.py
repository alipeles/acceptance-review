"""M2.3 acceptance: a dirty working tree produces the same change-set shape
as a committed diff (§5.1 — works before a PR exists)."""

import subprocess
from pathlib import Path

import pytest

from acceptance.change.diff import (
    WORKING_TREE_SENTINEL,
    extract_change_set,
    extract_working_tree_change_set,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    return path


def _shape(change_set):
    """(path, status, category) per file, ignoring revision identity — the
    comparable "shape" the acceptance check is about."""
    return sorted((f.path, f.status, f.category) for f in change_set.files)


def test_dirty_working_tree_matches_committed_diff_shape(tmp_path, repo):
    (repo / "tests").mkdir()
    (repo / "pkg.py").write_text("def f():\n    return 1\n")
    (repo / "tests" / "test_pkg.py").write_text("def test_f():\n    assert True\n")
    (repo / "requirements.txt").write_text("requests==2.0\n")
    base = _commit(repo, "base")

    # Make the same edits in two separate checkouts of the same base: one left
    # uncommitted (working-tree mode), one committed (M2.1 mode).
    working_repo = repo
    (working_repo / "pkg.py").write_text("def f():\n    return 2\n")
    (working_repo / "tests" / "test_pkg.py").write_text(
        "def test_f():\n    assert True\n\n\ndef test_g():\n    assert True\n"
    )
    (working_repo / "requirements.txt").write_text("requests==3.0\n")
    # Stage one file and leave the others unstaged, to prove both are included.
    _git(working_repo, "add", "pkg.py")

    working_tree_result = extract_working_tree_change_set(working_repo, base)

    committed_repo = tmp_path / "committed"
    subprocess.run(["git", "clone", "-q", str(repo), str(committed_repo)], check=True, capture_output=True)
    _git(committed_repo, "checkout", "-q", base)
    (committed_repo / "pkg.py").write_text("def f():\n    return 2\n")
    (committed_repo / "tests" / "test_pkg.py").write_text(
        "def test_f():\n    assert True\n\n\ndef test_g():\n    assert True\n"
    )
    (committed_repo / "requirements.txt").write_text("requests==3.0\n")
    head = _commit(committed_repo, "head")
    committed_result = extract_change_set(committed_repo, base, head)

    assert _shape(working_tree_result) == _shape(committed_result)
    # Every file has real hunks in both modes.
    for result in (working_tree_result, committed_result):
        for file_change in result.files:
            assert file_change.hunks

    assert working_tree_result.head_revision == WORKING_TREE_SENTINEL
    assert working_tree_result.base_revision == base


def test_untracked_new_file_is_detected_as_added(repo):
    (repo / "pkg.py").write_text("x = 1\n")
    base = _commit(repo, "base")

    (repo / "new_module.py").write_text("y = 2\nz = 3\n")

    change_set = extract_working_tree_change_set(repo, base)

    assert len(change_set.files) == 1
    added = change_set.files[0]
    assert added.path == "new_module.py"
    assert added.status == "added"
    assert added.category == "source"
    assert added.hunks
    assert "+y = 2" in added.hunks[0].content
    assert "+z = 3" in added.hunks[0].content


def test_staged_and_unstaged_changes_are_both_included(repo):
    (repo / "a.py").write_text("a = 1\n")
    (repo / "b.py").write_text("b = 1\n")
    base = _commit(repo, "base")

    (repo / "a.py").write_text("a = 2\n")
    _git(repo, "add", "a.py")  # staged
    (repo / "b.py").write_text("b = 2\n")  # unstaged

    change_set = extract_working_tree_change_set(repo, base)

    paths = {f.path for f in change_set.files}
    assert paths == {"a.py", "b.py"}


def test_no_commits_after_base_are_required(repo):
    """Working-tree mode never needs a head commit — only uncommitted state."""
    (repo / "pkg.py").write_text("x = 1\n")
    base = _commit(repo, "base")
    (repo / "pkg.py").write_text("x = 2\n")

    change_set = extract_working_tree_change_set(repo, base)

    assert change_set.head_revision == WORKING_TREE_SENTINEL
    assert len(change_set.files) == 1


def test_deleted_file_in_working_tree_is_detected(repo):
    (repo / "gone.py").write_text("x = 1\n")
    base = _commit(repo, "base")
    (repo / "gone.py").unlink()

    change_set = extract_working_tree_change_set(repo, base)

    assert len(change_set.files) == 1
    assert change_set.files[0].status == "deleted"
    assert change_set.files[0].path == "gone.py"


def test_unstaged_plain_mv_is_not_detected_as_a_rename(repo):
    """Documented limitation: an untracked rename (mv without git add/git mv)
    is seen as a deletion + a separate untracked addition."""
    (repo / "old_name.py").write_text("x = 1\n")
    base = _commit(repo, "base")
    (repo / "old_name.py").rename(repo / "new_name.py")

    change_set = extract_working_tree_change_set(repo, base)

    statuses = {f.path: f.status for f in change_set.files}
    assert statuses == {"old_name.py": "deleted", "new_name.py": "added"}


def test_staged_rename_is_detected_correctly(repo):
    (repo / "old_name.py").write_text("x = 1\ny = 2\nz = 3\n")
    base = _commit(repo, "base")
    _git(repo, "mv", "old_name.py", "new_name.py")

    change_set = extract_working_tree_change_set(repo, base)

    assert len(change_set.files) == 1
    renamed = change_set.files[0]
    assert renamed.status == "renamed"
    assert renamed.path == "new_name.py"
    assert renamed.old_path == "old_name.py"


def test_no_changes_yields_empty_change_set(repo):
    (repo / "pkg.py").write_text("x = 1\n")
    base = _commit(repo, "base")

    change_set = extract_working_tree_change_set(repo, base)
    assert change_set.files == []
