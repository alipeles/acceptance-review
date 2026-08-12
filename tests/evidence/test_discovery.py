"""M4.1 acceptance: on a fixture where an existing untouched test covers a
changed function, that test is discovered — plus unit coverage of each
discovery signal (added/modified, call graph, touched-not-called reference,
import, naming) and the file-scan budget."""

import subprocess
from pathlib import Path

import pytest

from acceptance.change.diff import extract_change_set
from acceptance.evidence.discovery import (
    DiscoveryReason,
    TestDiscoveryBudget,
    discover_tests,
)
from acceptance.review_state import ChangeSet, DiffHunk, FileChange


def _hunk(new_start: int, new_lines: int) -> DiffHunk:
    return DiffHunk(
        header=f"@@ -{new_start},{new_lines} +{new_start},{new_lines} @@",
        old_start=new_start,
        old_lines=new_lines,
        new_start=new_start,
        new_lines=new_lines,
        content="",
    )


def _change_set(*files: FileChange) -> ChangeSet:
    return ChangeSet(base_revision="base", head_revision="head", files=list(files))


def _source_change(
    path: str, new_start: int = 1, new_lines: int = 2, status: str = "modified"
) -> FileChange:
    return FileChange(
        path=path, status=status, category="source", hunks=[_hunk(new_start, new_lines)]
    )


def _test_change(path: str, status: str = "added") -> FileChange:
    return FileChange(path=path, status=status, category="test", hunks=[_hunk(1, 3)])


def _write(repo: Path, name: str, content: str) -> None:
    (repo / name).write_text(content)


# --- unit-level: hand-built change sets, no git needed ---


def test_added_test_file_contributes_every_test_it_defines(tmp_path):
    repo = tmp_path
    _write(
        repo,
        "test_new.py",
        "def test_a():\n    assert True\n\n\ndef test_b():\n    assert True\n",
    )
    change_set = _change_set(_test_change("test_new.py"))

    result = discover_tests(repo, change_set)

    test_ids = {t.test_id for t in result.tests}
    assert test_ids == {"test_new.py::test_a", "test_new.py::test_b"}
    assert all(t.reasons == [DiscoveryReason.ADDED_OR_MODIFIED] for t in result.tests)


def test_class_based_test_method_gets_a_pytest_style_node_id(tmp_path):
    repo = tmp_path
    _write(
        repo,
        "test_new.py",
        "class TestThing:\n    def test_it(self):\n        assert True\n",
    )
    change_set = _change_set(_test_change("test_new.py"))

    result = discover_tests(repo, change_set)

    assert result.tests[0].test_id == "test_new.py::TestThing::test_it"


def test_deleted_test_file_is_not_discovered(tmp_path):
    repo = tmp_path
    change_set = _change_set(_test_change("test_gone.py", status="deleted"))

    result = discover_tests(repo, change_set)

    assert result.tests == []


def test_untouched_test_calling_a_changed_symbol_is_discovered_by_call_graph(tmp_path):
    repo = tmp_path
    _write(repo, "mod.py", "def target():\n    return 1\n")
    _write(
        repo,
        "test_mod.py",
        "from mod import target\n\n\ndef test_target():\n    assert target() == 1\n",
    )
    # mod.py changed; test_mod.py is untouched (not in the change set).
    change_set = _change_set(_source_change("mod.py", new_start=1, new_lines=2))

    result = discover_tests(repo, change_set)

    found = next(t for t in result.tests if t.test_id == "test_mod.py::test_target")
    assert DiscoveryReason.CALLS_CHANGED_SYMBOL in found.reasons


def test_untouched_test_referencing_without_calling_is_a_distinct_reason(tmp_path):
    repo = tmp_path
    _write(repo, "mod.py", "class Thing:\n    pass\n")
    _write(
        repo,
        "test_mod.py",
        "from mod import Thing\n\n\ndef test_is_thing():\n    assert isinstance(object(), Thing) is False\n",
    )
    change_set = _change_set(_source_change("mod.py", new_start=1, new_lines=2))

    result = discover_tests(repo, change_set)

    found = next(t for t in result.tests if t.test_id == "test_mod.py::test_is_thing")
    assert DiscoveryReason.REFERENCES_CHANGED_SYMBOL in found.reasons
    assert DiscoveryReason.CALLS_CHANGED_SYMBOL not in found.reasons


def test_untouched_test_importing_the_changed_module_is_discovered(tmp_path):
    repo = tmp_path
    _write(repo, "mod.py", "def unrelated_helper():\n    return 1\nCONST = 2\n")
    _write(
        repo,
        "test_mod.py",
        "import mod\n\n\ndef test_const():\n    assert mod.CONST == 2\n",
    )
    # Change targets a *different* symbol than the test touches, so the only
    # signal available is the module-level import.
    change_set = _change_set(_source_change("mod.py", new_start=1, new_lines=2))

    result = discover_tests(repo, change_set)

    found = next((t for t in result.tests if t.test_id == "test_mod.py::test_const"), None)
    assert found is not None
    assert DiscoveryReason.IMPORTS_CHANGED_MODULE in found.reasons


def test_untouched_test_named_after_the_changed_symbol_is_discovered(tmp_path):
    repo = tmp_path
    _write(repo, "mod.py", "def widget():\n    return 1\n")
    _write(
        repo,
        "test_mod.py",
        "def test_widget_behavior():\n    from mod import widget\n    assert widget\n",
    )
    change_set = _change_set(_source_change("mod.py", new_start=1, new_lines=2))

    result = discover_tests(repo, change_set)

    found = next(t for t in result.tests if t.test_id == "test_mod.py::test_widget_behavior")
    assert DiscoveryReason.NAME_MATCHES_SYMBOL in found.reasons


def test_unrelated_test_is_not_discovered(tmp_path):
    repo = tmp_path
    _write(repo, "mod.py", "def target():\n    return 1\n")
    _write(
        repo,
        "test_other.py",
        "def test_unrelated():\n    assert 1 + 1 == 2\n",
    )
    change_set = _change_set(_source_change("mod.py", new_start=1, new_lines=2))

    result = discover_tests(repo, change_set)

    assert result.tests == []


def test_file_scan_budget_is_respected_and_flagged(tmp_path):
    repo = tmp_path
    for i in range(3):
        _write(repo, f"test_{i}.py", "def test_x():\n    assert True\n")
    change_set = _change_set()

    result = discover_tests(repo, change_set, budget=TestDiscoveryBudget(max_files_scanned=1))

    assert result.files_scanned == 1
    assert result.files_scanned_truncated is True


# --- acceptance: real git repo, real extract_change_set (M4.1's own wording) ---


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


def test_existing_untouched_test_covering_a_changed_function_is_discovered(repo):
    (repo / "mod.py").write_text("def f():\n    return 1\n")
    (repo / "test_mod.py").write_text("from mod import f\n\n\ndef test_f():\n    assert f() == 1\n")
    base = _commit(repo, "base")

    (repo / "mod.py").write_text("def f():\n    return 2\n")
    head = _commit(repo, "head")

    change_set = extract_change_set(repo, base, head)
    result = discover_tests(repo, change_set)

    test_ids = {t.test_id for t in result.tests}
    assert "test_mod.py::test_f" in test_ids
