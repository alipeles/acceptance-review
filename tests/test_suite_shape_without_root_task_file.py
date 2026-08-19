"""Neither the suite's shape nor its outcome depends on the root task file (#258).

`tests/test_root_task_file_is_not_read.py` bans the *pattern* — a repository-root
name joined to `current-task.md` — by scanning test sources. That is a static
guard, and it can only catch the shape it knows. These two tests assert the
property itself, by running the suite against a repository snapshot in which the
root task file is the only thing that changes:

- collection is identical with the file absent and with it present, so no test's
  outcome, case list or id moves with it;
- the tests that used to read it pass when it is absent entirely, which is the
  fresh-clone case that failed outright before #258.

They are the expensive half of the pair — one copy of the tree and three
subprocess `pytest` runs, about fifteen seconds. The static guard is what runs on
every edit; this is what makes the guard's claim falsifiable.

One snapshot serves both, and the same directory is reused for the two
collections rather than a directory each. That is deliberate: it makes the
comparison controlled — the two runs differ in the root task file and in nothing
else, not even the path they run from — and the parametrize ids in
`test_region_coverage.py` are absolute paths, so two directories would differ in
every corpus id for a reason that has nothing to do with the property.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Enough of the tree to run the suite: the package, the tests, the committed
# corpus the parametrized cases are built from, and the pytest configuration
# (`pythonpath` and `addopts` are both cwd-relative, so the snapshot must carry
# them or the inner run collects a different set of files).
_SNAPSHOT_PARTS = ("src", "tests", "dogfood-logs", "pyproject.toml")

# The two modules that read the root task file before #258, plus the corpus
# properties that replaced it.
_AFFECTED = (
    "tests/requirement/test_task_file.py",
    "tests/requirement/test_region_coverage.py",
    "tests/requirement/test_task_file_corpus.py",
)

_INNER = "ACCEPTANCE_INNER_SUITE"

# A snapshot's own copy of this module must not run the snapshots again.
pytestmark = pytest.mark.skipif(
    os.environ.get(_INNER) == "1",
    reason="inner suite run: the snapshot tests do not recurse",
)


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A copy of the tree with no root task file, shared by both tests."""
    dest = tmp_path_factory.mktemp("snapshot")
    for part in _SNAPSHOT_PARTS:
        source = REPO_ROOT / part
        if source.is_dir():
            shutil.copytree(
                source,
                dest / part,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
                symlinks=True,
            )
        else:
            shutil.copy2(source, dest / part)
    assert not (dest / "current-task.md").exists()
    return dest


def _run_pytest(snapshot: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *args],
        cwd=snapshot,
        env={**os.environ, _INNER: "1"},
        capture_output=True,
        text=True,
        # The exit code is the assertion; a non-zero one must reach the test
        # with its output rather than raise here.
        check=False,
    )


def _outcome(result: subprocess.CompletedProcess[str]) -> str:
    """The `-q` summary without its timing — `"265 passed"`, `"1 failed, 264 passed"`.

    Timing is the only part of that line that moves between two runs of the same
    tests, so stripping it leaves a value that must be equal across the pair.
    """
    for line in reversed(result.stdout.splitlines()):
        if " in " in line and ("passed" in line or "failed" in line or "error" in line):
            return line.split(" in ")[0].strip()
    return result.stdout[-500:]


def _collected_ids(result: subprocess.CompletedProcess[str]) -> list[str]:
    """The node ids `--collect-only -q` printed, without its timing summary."""
    return [
        line.strip()
        for line in result.stdout.splitlines()
        if "::" in line and not line.startswith(("=", "ERROR", "FAILED"))
    ]


def test_collection_is_identical_with_and_without_the_root_task_file(snapshot: Path):
    """The property #258 exists to get.

    The old `_committed_task_files` put the root file at the head of a
    parametrize, so the number of tests and their ids were computed at
    collection time from an uncommitted working file. Counting alone would not
    catch that — and would be actively misleading here, since the corpus grows
    by one case per dogfood run — so the two collections are compared id by id.
    """
    task_file = snapshot / "current-task.md"
    try:
        absent = _run_pytest(snapshot, "--collect-only", "-q")
        task_file.write_text("# Task\nA task file that is not part of the corpus.\n")
        present = _run_pytest(snapshot, "--collect-only", "-q")
    finally:
        task_file.unlink(missing_ok=True)

    assert absent.returncode == 0, absent.stdout[-2000:]
    assert present.returncode == absent.returncode, present.stdout[-2000:]

    absent_ids = _collected_ids(absent)
    present_ids = _collected_ids(present)

    # Not vacuous: collection really happened, and it reached the cases built
    # from the committed corpus.
    assert len(absent_ids) > 100
    assert any("test_parses_every_committed_task_file" in i for i in absent_ids)

    assert absent_ids == present_ids


def test_the_affected_tests_have_the_same_outcome_with_and_without_it(snapshot: Path):
    """Outcomes, not only the case list.

    A fresh clone has no `current-task.md`, and before #258 the parse test raised
    `FileNotFoundError` there before reaching an assertion — so the absent run
    has to pass. But collection can be identical while an *outcome* still moves:
    a test that reads the file to compute an expected value keeps its id and
    changes what it asserts. That is why both states are run and compared rather
    than only the absent one.
    """
    task_file = snapshot / "current-task.md"
    assert not task_file.exists()
    try:
        absent = _run_pytest(snapshot, "-q", *_AFFECTED)
        task_file.write_text("# Task\nA task file that is not part of the corpus.\n")
        present = _run_pytest(snapshot, "-q", *_AFFECTED)
    finally:
        task_file.unlink(missing_ok=True)

    assert absent.returncode == 0, absent.stdout[-4000:]
    assert present.returncode == absent.returncode, present.stdout[-4000:]

    # Not vacuous, and not quietly skipped: the affected tests really ran.
    assert " passed" in absent.stdout
    assert "no tests ran" not in absent.stdout
    assert "skipped" not in absent.stdout, absent.stdout[-2000:]

    assert _outcome(absent) == _outcome(present)
