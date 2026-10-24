"""Throwaway copies of the project under review.

Separate from `injection.py` on purpose, and not only for tidiness: the control
run needs an unmodified copy, and the control run is established in
`baseline.py`, which `review_state.py` imports. Importing the mutation machinery
from there closes a loop back through the change-set model. This module imports
nothing of ours, so it can be depended on from either side.

Every mutant is observed in a copy so nothing is applied to a working tree
somebody is using — a mutation restored afterwards is one crash away from
leaving a deliberately broken file behind, inside a stage whose whole job is to
break things.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

__all__ = ["LINKED", "SKIPPED", "copied_project"]

#: Directory names never copied into a workspace.
#:
#: Every entry is a *tool's* directory rather than any project's source, which
#: is what keeps the list generic: none is here because this repository has it,
#: and a project that genuinely keeps source in one of them is caught by the
#: faithfulness check in `baseline.py` rather than silently mis-reviewed.
#:
#: `__pycache__` is a correctness requirement rather than an optimization: stale
#: bytecode whose source has just been mutated is exactly how an injected defect
#: fails to take effect.
#:
#: The rest are size. One copy per defect means this list is multiplied by the
#: defect count — on this repository `.acceptance` alone held 7,531 cached
#: transcript files, and copying those seventy times would dwarf the test runs
#: the copies exist for.
SKIPPED = frozenset(
    {
        # Version control history: large, and a project whose tests inspect it
        # is the case the faithfulness check exists for.
        ".git",
        ".hg",
        ".svn",
        # Regenerated caches.
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".hypothesis",
        "htmlcov",
        # Dependency trees. Not copied, but a `.venv` is linked back to the
        # original — see `LINKED`.
        ".venv",
        "node_modules",
        # Editor state.
        ".idea",
        ".vscode",
        # Our own run artifacts inside the project under review: our cache, not
        # the project's code.
        ".acceptance",
    }
)


#: Skipped directories that the copy gets as a link to the original instead.
#:
#: A user's test command names its interpreter by a path inside the project —
#: `cd api && .venv/bin/python -m pytest` — and the command runs inside the
#: copy. Without the link that path does not exist there, every test passes in
#: the project and fails in the unmodified copy, and the faithfulness check sets
#: every one aside (#405). A link, not a copy: a virtualenv is large, and one
#: copy per defect multiplies it. The tests never write to it, and
#: `shutil.rmtree` removes the link without following it, so the original is
#: untouched when the workspace goes.
LINKED = frozenset({".venv"})


@contextmanager
def copied_project(
    project_root: Path, prefix: str, link_environments: bool = True
) -> Iterator[Path]:
    """A copy of `project_root`, removed on exit. Yields the copy's root.

    `link_environments=False` leaves out the `LINKED` links too. A copy handed
    to a coding agent to edit takes that: nothing it runs needs the project's
    interpreter, and a link would let an edit reach the original through it.

    The copy keeps the project's own directory basename. pytest finds its
    rootdir and its configuration by walking up from where it is invoked, and a
    project whose tests assert on paths would see a different tree under a
    renamed root.

    `project_root.resolve()` matters: `Path(".").name` is the empty string, and
    the destination would then be the workspace directory itself — which already
    exists, so the copy fails and nothing runs. The CLI passes `Path(".")` as a
    matter of course, so that was every real run.
    """
    workspace = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        source = project_root.resolve()
        root = workspace / (source.name or "project")
        linked: list[Path] = []

        def ignore(directory: str, names: list[str]) -> set[str]:
            skipped = {name for name in names if name in SKIPPED}
            if not link_environments:
                return skipped
            linked.extend(
                Path(directory, name) for name in skipped & LINKED if Path(directory, name).is_dir()
            )
            return skipped

        shutil.copytree(source, root, ignore=ignore, symlinks=True)
        for original in linked:
            (root / original.relative_to(source)).symlink_to(original, target_is_directory=True)
        yield root
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
