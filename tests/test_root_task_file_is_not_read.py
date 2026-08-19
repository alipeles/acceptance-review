"""No test reads the repository-root task file (#258).

`current-task.md` at the repository root is a scratch input: rewritten for every
task, edited mid-task, and absent entirely from a fresh clone. A test that reads
it has an outcome — and, through a collection-time parametrize, a *shape* — that
depends on work in flight rather than on the code.

This is a standing guard rather than a one-off cleanup, because the two call
sites #258 removed were both written in good faith: reaching for the repository's
own task file is a natural thing to do, and nothing else would notice.

It deliberately does **not** ban the filename. `tests/test_cli.py` writes a
`current-task.md` into a temporary git repository fixture, which is exactly what
the CLI is for and must keep working; `tests/benchmark/` reads the committed
`dogfood-logs/*/current-task.md` corpus. What is banned is joining the *root of
this repository* to that name.
"""

from __future__ import annotations

import re
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TESTS_ROOT.parent

# A name for this repository's root, joined *directly* to the task file name —
# a `REPO_ROOT`, `repo_root`, `REPO`, `root` or `parents[N]` on the left, and
# the quoted task file name immediately on the right. An intervening component
# (a run directory, a fixture directory, a temp path) means the target is a
# committed input or a fixture, not the scratch file, and is not matched.
_ROOT_TASK_FILE = re.compile(
    r"""(?:REPO_ROOT|REPO|repo_root|root|parents\[\d+\])\s*/\s*["']current-task\.md["']"""
)

# The banned shape is assembled here rather than written out, so that this file
# — the one place that must talk about the shape in order to ban it — does not
# itself contain it. The assembled values are byte-for-byte the real lines.
_TASK_FILE_NAME = '"current-task' + '.md"'


def _test_sources() -> list[Path]:
    """Every test source the guard scans — including this one.

    Scanning itself is why `_TASK_FILE_NAME` exists: the first version of this
    module wrote the banned shape out in its comments and fixtures and promptly
    failed its own assertion, so the shape is assembled instead. Excluding this
    file would have been the easier fix and a worse one — it is the file most
    likely to reintroduce the pattern by accident.
    """
    return sorted(p for p in TESTS_ROOT.rglob("*.py") if "fixtures" not in p.parts)


def test_no_test_source_reads_the_repository_root_task_file():
    offenders = []
    for path in _test_sources():
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if _ROOT_TASK_FILE.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")

    assert not offenders, (
        "these read the repository-root task file, a scratch input no commit "
        "governs; use tests.requirement.corpus.committed_task_files() instead:\n"
        + "\n".join(offenders)
    )


def test_the_scan_actually_reads_this_repositorys_tests():
    """Without this the guard above passes on an empty file list."""
    sources = _test_sources()
    assert len(sources) > 20
    assert TESTS_ROOT / "requirement" / "test_task_file.py" in sources


def test_the_scan_covers_helper_modules_and_conftest_too():
    """Not only files named `test_*.py`.

    Both call sites #258 removed lived in helpers — `_committed_task_files` and
    a module-level read — not in a test function, and a read reached from a
    fixture in `conftest.py` would be just as load-bearing. The `fixtures`
    exclusion in `_test_sources` is the one place this could quietly narrow, so
    the two kinds of file are named here rather than assumed.
    """
    sources = set(_test_sources())

    assert TESTS_ROOT / "conftest.py" in sources
    assert TESTS_ROOT / "requirement" / "corpus.py" in sources
    assert any(p.name != "conftest.py" and not p.name.startswith("test_") for p in sources)

    # The `fixtures` exclusion drops those files and nothing else. Without this,
    # a widened exclusion — one more directory name, a typo that matches a real
    # package — silently shrinks what the guard above can see, and the guard
    # goes green by looking at less.
    skipped = set(TESTS_ROOT.rglob("*.py")) - sources
    assert skipped, "the exclusion is meant to drop the archetype fixtures"
    assert all("fixtures" in p.parts for p in skipped)


def test_the_pattern_matches_the_call_sites_258_removed():
    """The two real pre-#258 lines. A pattern that stopped matching these would
    leave the guard green while the defect returned."""
    assert _ROOT_TASK_FILE.search(f"    files = [REPO_ROOT / {_TASK_FILE_NAME}]")
    assert _ROOT_TASK_FILE.search(
        f"    parsed = parse_task_file((repo_root / {_TASK_FILE_NAME}).read_text())"
    )


def test_the_pattern_allows_committed_and_fixture_paths():
    """The shapes that must keep working, also verbatim from the suite."""
    assert not _ROOT_TASK_FILE.search('    task_path = git_repo["path"] / "current-task.md"')
    assert not _ROOT_TASK_FILE.search(
        '    corpus_task = (CORPUS_DIR / "167-gate2-run3" / "current-task.md").read_text()'
    )
    assert not _ROOT_TASK_FILE.search(
        '    require_nonempty_registry(case_dir.name, (REPO / meta.run_dir / "current-task.md").read_text())'
    )
    assert not _ROOT_TASK_FILE.search(
        '    return [p for p in sorted(root.glob("dogfood-logs/*/current-task.md")) if p.is_file()]'
    )
