"""M2.1 acceptance: on a fixture with a source edit, a test edit, and a
dependency bump, all three are correctly categorized."""

import subprocess
from pathlib import Path

import pytest

from acceptance.change.diff import extract_change_set


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


def test_source_test_and_dependency_edits_are_correctly_categorized(repo):
    (repo / "tests").mkdir()
    (repo / "pkg.py").write_text("def f():\n    return 1\n")
    (repo / "tests" / "test_pkg.py").write_text("def test_f():\n    assert True\n")
    (repo / "requirements.txt").write_text("requests==2.0\n")
    base = _commit(repo, "base")

    (repo / "pkg.py").write_text("def f():\n    return 2\n")
    (repo / "tests" / "test_pkg.py").write_text("def test_f():\n    assert True\n\n\ndef test_g():\n    assert True\n")
    (repo / "requirements.txt").write_text("requests==3.0\n")
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head)

    by_path = {f.path: f for f in change_set.files}
    assert set(by_path) == {"pkg.py", "tests/test_pkg.py", "requirements.txt"}

    assert by_path["pkg.py"].category == "source"
    assert by_path["pkg.py"].status == "modified"
    assert by_path["pkg.py"].hunks

    assert by_path["tests/test_pkg.py"].category == "test"
    assert by_path["tests/test_pkg.py"].status == "modified"
    assert by_path["tests/test_pkg.py"].hunks

    assert by_path["requirements.txt"].category == "config"
    assert by_path["requirements.txt"].status == "modified"
    assert by_path["requirements.txt"].hunks


def test_hunk_content_is_captured_correctly(repo):
    (repo / "pkg.py").write_text("line1\nline2\nline3\n")
    base = _commit(repo, "base")
    (repo / "pkg.py").write_text("line1\nCHANGED\nline3\n")
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head)
    hunk = change_set.files[0].hunks[0]

    assert hunk.old_start == 1
    assert hunk.new_start == 1
    assert "-line2" in hunk.content
    assert "+CHANGED" in hunk.content


def test_added_file_is_detected(repo):
    (repo / "existing.py").write_text("x = 1\n")
    base = _commit(repo, "base")
    (repo / "new_module.py").write_text("y = 2\n")
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head)
    assert len(change_set.files) == 1
    added = change_set.files[0]
    assert added.path == "new_module.py"
    assert added.status == "added"
    assert added.category == "source"
    assert added.hunks


def test_deleted_file_is_detected(repo):
    (repo / "gone.py").write_text("x = 1\n")
    base = _commit(repo, "base")
    (repo / "gone.py").unlink()
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head)
    assert len(change_set.files) == 1
    deleted = change_set.files[0]
    assert deleted.path == "gone.py"
    assert deleted.status == "deleted"
    assert deleted.old_path is None
    assert deleted.hunks


def test_renamed_file_is_detected(repo):
    (repo / "old_name.py").write_text("def f():\n    return 1\ndef g():\n    return 2\n")
    base = _commit(repo, "base")
    _git(repo, "mv", "old_name.py", "new_name.py")
    (repo / "new_name.py").write_text("def f():\n    return 1\ndef g():\n    return 3\n")
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head)
    assert len(change_set.files) == 1
    renamed = change_set.files[0]
    assert renamed.path == "new_name.py"
    assert renamed.old_path == "old_name.py"
    assert renamed.status == "renamed"
    assert renamed.hunks  # content changed too


def test_no_changes_between_identical_revisions(repo):
    (repo / "pkg.py").write_text("x = 1\n")
    base = _commit(repo, "base")

    change_set = extract_change_set(repo, base, base)
    assert change_set.files == []


def test_multi_hunk_file_produces_multiple_hunks(repo):
    lines = [f"line{i}\n" for i in range(1, 41)]
    (repo / "pkg.py").write_text("".join(lines))
    base = _commit(repo, "base")

    lines[2] = "CHANGED_NEAR_TOP\n"
    lines[35] = "CHANGED_NEAR_BOTTOM\n"
    (repo / "pkg.py").write_text("".join(lines))
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head)
    assert len(change_set.files[0].hunks) == 2


@pytest.mark.parametrize(
    ("filename", "expected_category"),
    [
        ("pyproject.toml", "config"),
        ("setup.py", "config"),
        ("Pipfile.lock", "config"),
        ("poetry.lock", "config"),
        ("package.json", "config"),
        ("requirements-dev.txt", "config"),
        ("README.md", "other"),
        ("src/pkg/module.py", "source"),
        ("tests/test_module.py", "test"),
        ("src/pkg/module_test.py", "test"),
    ],
)
def test_categorization_by_filename(repo, filename, expected_category):
    path = repo / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("content v1\n")
    base = _commit(repo, "base")
    path.write_text("content v2\n")
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head)
    assert change_set.files[0].category == expected_category


# --- ignore patterns (#105) ---


def test_no_ignore_file_leaves_behavior_unchanged(repo):
    (repo / "pkg.py").write_text("x = 1\n")
    base = _commit(repo, "base")
    (repo / "pkg.py").write_text("x = 2\n")
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head)
    assert change_set.ignored_paths == []
    assert len(change_set.files) == 1


def test_acceptance_ignore_file_excludes_matching_paths(repo):
    (repo / "vendor").mkdir()
    (repo / "vendor" / "lib.py").write_text("x = 1\n")
    (repo / "pkg.py").write_text("x = 1\n")
    base = _commit(repo, "base")

    (repo / ".acceptance").mkdir()
    (repo / ".acceptance" / "ignore").write_text("vendor/\n")
    (repo / "vendor" / "lib.py").write_text("x = 2\n")
    (repo / "pkg.py").write_text("x = 2\n")
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head)

    by_path = {f.path: f for f in change_set.files}
    assert "vendor/lib.py" not in by_path
    assert "pkg.py" in by_path
    assert "vendor/lib.py" in change_set.ignored_paths
    assert "pkg.py" not in change_set.ignored_paths
    # The ignore file itself is a change too, and isn't self-excluded.
    assert ".acceptance/ignore" in by_path


def test_extra_ignore_patterns_are_applied(repo):
    (repo / "pkg.py").write_text("x = 1\n")
    (repo / "other.py").write_text("x = 1\n")
    base = _commit(repo, "base")
    (repo / "pkg.py").write_text("x = 2\n")
    (repo / "other.py").write_text("x = 2\n")
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head, extra_ignore_patterns=["pkg.py"])

    by_path = {f.path: f for f in change_set.files}
    assert "pkg.py" not in by_path
    assert "other.py" in by_path
    assert change_set.ignored_paths == ["pkg.py"]


def test_extra_ignore_patterns_add_to_not_replace_the_ignore_file(repo):
    (repo / "vendor").mkdir()
    (repo / "vendor" / "lib.py").write_text("x = 1\n")
    (repo / "pkg.py").write_text("x = 1\n")
    (repo / "task.md").write_text("v1\n")
    base = _commit(repo, "base")

    (repo / ".acceptance").mkdir()
    (repo / ".acceptance" / "ignore").write_text("vendor/\n")
    (repo / "vendor" / "lib.py").write_text("x = 2\n")
    (repo / "pkg.py").write_text("x = 2\n")
    (repo / "task.md").write_text("v2\n")
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head, extra_ignore_patterns=["/task.md"])

    by_path = {f.path: f for f in change_set.files}
    # Both the file-based pattern (vendor/) and the extra pattern (task.md)
    # apply together — extra patterns don't disable the repo's own config.
    assert "vendor/lib.py" not in by_path
    assert "task.md" not in by_path
    assert "pkg.py" in by_path
    assert set(change_set.ignored_paths) == {"vendor/lib.py", "task.md"}


def test_ignore_patterns_apply_to_untracked_working_tree_files(repo):
    from acceptance.change.diff import extract_working_tree_change_set

    (repo / "pkg.py").write_text("x = 1\n")
    base = _commit(repo, "base")

    (repo / "vendor").mkdir()
    (repo / "vendor" / "lib.py").write_text("x = 1\n")  # untracked
    (repo / "new_module.py").write_text("y = 1\n")  # untracked

    change_set = extract_working_tree_change_set(repo, base, extra_ignore_patterns=["vendor/"])

    by_path = {f.path: f for f in change_set.files}
    assert "vendor/lib.py" not in by_path
    assert "new_module.py" in by_path
    assert "vendor/lib.py" in change_set.ignored_paths


def test_read_ignore_patterns_returns_empty_when_file_absent(repo):
    from acceptance.change.diff import read_ignore_patterns

    assert read_ignore_patterns(repo) == []


def test_read_ignore_patterns_reads_the_file(repo):
    from acceptance.change.diff import read_ignore_patterns

    (repo / ".acceptance").mkdir()
    (repo / ".acceptance" / "ignore").write_text("# a comment\nvendor/\n*.log\n")

    assert read_ignore_patterns(repo) == ["# a comment", "vendor/", "*.log"]
