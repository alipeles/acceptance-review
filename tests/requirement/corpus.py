"""The repository's committed task-file corpus (#258).

Every dogfood run commits the exact task file it was given, alongside the output
it produced, and never edits it again. That makes `dogfood-logs/*/current-task.md`
a stable corpus: it only grows, and each entry is governed by a commit.

The repository-root `current-task.md` is deliberately **not** part of it. That
file is a scratch input — rewritten for every task, and edited mid-task by the
Gate 1 procedure — so a test reading it has an outcome that depends on work in
flight rather than on the code. Worse, a parametrize built from it computes its
case list at collection time, so the *number of tests and their ids* moved with
an uncommitted working file, and the suite could not be compared across runs.
A fresh clone with no `current-task.md` at all failed outright.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def committed_task_files(root: Path = REPO_ROOT) -> list[Path]:
    """Every committed dogfood run's task file, in stable order.

    `is_file()` is belt-and-braces, and measured to be so: `glob` resolves a
    literal final component through `exists()`, so a pruned entry or a symlink
    whose target is gone never reaches this filter in the first place. Removing
    the filter changes no result — verified by injection, not assumed. It is
    kept because it costs nothing and states the intent, but it is **not** what
    makes the "an absent path is not a case" property hold, and no test here
    discriminates it.
    """
    return [p for p in sorted(root.glob("dogfood-logs/*/current-task.md")) if p.is_file()]
