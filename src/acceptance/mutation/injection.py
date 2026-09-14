"""Applies a mutant to a throwaway copy of the project, never to the original.

The mandate's word is "a throwaway copy", and it is load-bearing rather than
tidy. The review runs against a working tree someone is using; a mutation
applied in place and restored afterwards is one crash away from leaving a
deliberately broken file behind, and the crash would happen inside a stage whose
whole job is to break things.

Copying is also what makes the run repeatable. Each defect gets its own copy, so
one mutant can never be observed on top of another, and a test that fails under
two mutants fails under each of them independently.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from acceptance.mutation.attempt import MutationDescriptor
from acceptance.mutation.validity import apply_span

__all__ = ["mutated_copy"]

#: Directory names never copied into the mutant workspace. Each is either
#: regenerated on demand or enormous, and `__pycache__` is worse than useless:
#: a stale bytecode file whose source has been mutated is exactly the way an
#: injected defect fails to take effect.
_SKIPPED = frozenset({".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})


@contextmanager
def mutated_copy(
    project_root: Path,
    descriptor: MutationDescriptor,
) -> Iterator[Path]:
    """A copy of `project_root` with `descriptor` applied, removed on exit.

    Yields the root of the copy. The caller runs tests against it and never
    against `project_root`.

    Raises `FileNotFoundError` if the descriptor names a file the project does
    not have. That is a programming error rather than an ordinary outcome — the
    path came from the change set, so a missing file means the two disagree —
    and the runner turns it into a `not_mutable` attempt with the reason.
    """
    workspace = Path(tempfile.mkdtemp(prefix="acceptance-mutant-"))
    try:
        root = workspace / project_root.name
        shutil.copytree(project_root, root, ignore=_ignore, symlinks=True)
        target = root / descriptor.path
        if not target.is_file():
            raise FileNotFoundError(
                f"{descriptor.path} is named by the change set but is not a file in the project"
            )
        source = target.read_text(encoding="utf-8")
        target.write_text(apply_span(source, descriptor), encoding="utf-8")
        yield root
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in _SKIPPED}
