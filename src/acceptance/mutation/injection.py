"""Applies a mutant to a throwaway copy of the project, never to the original.

The copying itself lives in `workspace.py`, which `baseline.py` also needs for
the control run and which imports nothing of ours. What is here is the one thing
specific to injection: writing the edit into the copy.

Each defect gets its own copy, so one mutant can never be observed on top of
another, and a test that fails under two mutants fails under each independently.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from acceptance.mutation.attempt import MutationDescriptor
from acceptance.mutation.validity import apply_span
from acceptance.mutation.workspace import copied_project

__all__ = ["mutated_copy"]


@contextmanager
def mutated_copy(
    project_root: Path,
    descriptor: MutationDescriptor,
) -> Iterator[Path]:
    """A copy of `project_root` with `descriptor` applied, removed on exit.

    Yields the root of the copy. The caller runs tests against it and never
    against `project_root`.

    Raises `FileNotFoundError` if the descriptor names a file the project does
    not have. That is a disagreement between the change set and the working
    tree rather than an ordinary outcome, and the runner turns it into a
    `not_mutable` attempt carrying the reason.
    """
    with copied_project(project_root, prefix="acceptance-mutant-") as root:
        target = root / descriptor.path
        if not target.is_file():
            raise FileNotFoundError(
                f"{descriptor.path} is named by the change set but is not a file in the project"
            )
        source = target.read_text(encoding="utf-8")
        target.write_text(apply_span(source, descriptor), encoding="utf-8")
        yield root
