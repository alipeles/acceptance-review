"""The committed task-file corpus is built from committed inputs only (#258).

The corpus feeds two parametrized suites, so what it contains decides both what
those suites assert and how many cases they have. These tests pin the two
properties that made the previous version depend on uncommitted work: the
repository-root scratch file is not in it, and an entry that is not really there
does not reach a case.
"""

from __future__ import annotations

from pathlib import Path

from tests.requirement.corpus import REPO_ROOT, committed_task_files


def test_the_corpus_is_not_empty():
    """A glob matching nothing turns every parametrized case into zero tests,
    which reports as a pass."""
    assert committed_task_files()


def test_no_corpus_path_lies_outside_dogfood_logs():
    for path in committed_task_files():
        relative = path.relative_to(REPO_ROOT)
        assert relative.parts[0] == "dogfood-logs", f"{relative} is not a committed dogfood input"
        assert relative.name == "current-task.md"


def test_the_repository_root_task_file_is_not_a_case(tmp_path: Path):
    """The whole point of #258: the scratch file in flight is not an input."""
    (tmp_path / "current-task.md").write_text("# Task\nthe task in flight\n")
    run = tmp_path / "dogfood-logs" / "999-gate1-run1"
    run.mkdir(parents=True)
    (run / "current-task.md").write_text("# Task\na committed run\n")

    assert committed_task_files(tmp_path) == [run / "current-task.md"]


def test_an_entry_whose_target_is_missing_is_omitted(tmp_path: Path):
    """`glob` yields a symlink whose target is gone; `read_text()` on it raises.

    This is what the `is_file()` filter is for, and it is the only way that
    filter can be exercised — a glob cannot otherwise produce a path that is
    not there.
    """
    logs = tmp_path / "dogfood-logs"
    real = logs / "998-gate1-run1" / "current-task.md"
    real.parent.mkdir(parents=True)
    real.write_text("# Task\na committed run\n")

    dangling = logs / "999-gate1-run1" / "current-task.md"
    dangling.parent.mkdir(parents=True)
    dangling.symlink_to(tmp_path / "gone" / "current-task.md")

    assert dangling.is_symlink()
    assert committed_task_files(tmp_path) == [real]
