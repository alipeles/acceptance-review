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

# A path expression rooted at this repository, joined directly to the task file:
# `REPO_ROOT / "current-task.md"`, `repo_root / 'current-task.md'`, or the
# `Path(__file__).resolve().parents[2] / "current-task.md"` shape that reaches
# the root without naming it. An intervening component — `REPO / meta.run_dir /
# "current-task.md"` — is a committed corpus path and is not matched.
_ROOT_TASK_FILE = re.compile(
    r"""(?:REPO_ROOT|REPO|repo_root|root|parents\[\d+\])\s*/\s*["']current-task\.md["']"""
)


def _test_sources() -> list[Path]:
    """Every test source the guard scans.

    This module is excluded from its own scan: it quotes the banned shape on
    purpose, both in the comment documenting the pattern and in the two tests
    that pin the pattern against the real pre-#258 lines. Those quotations are
    the guard's evidence, so they have to stay verbatim.
    """
    this_file = Path(__file__).resolve()
    return sorted(
        p
        for p in TESTS_ROOT.rglob("*.py")
        if "fixtures" not in p.parts and p.resolve() != this_file
    )


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


def test_the_pattern_matches_the_call_sites_258_removed():
    """The two real pre-#258 lines, verbatim. A pattern that stopped matching
    these would leave the guard green while the defect returned."""
    assert _ROOT_TASK_FILE.search('    files = [REPO_ROOT / "current-task.md"]')
    assert _ROOT_TASK_FILE.search(
        '    parsed = parse_task_file((repo_root / "current-task.md").read_text())'
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
