"""The mutant lands on a copy, and the original is never touched.

The mandate says "a throwaway copy", and the reason is not tidiness: a mutation
applied in place and restored afterwards is one crash away from leaving a
deliberately broken file in a working tree someone is using, inside a stage
whose whole job is to break things.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from acceptance.mutation.attempt import MutationDescriptor
from acceptance.mutation.injection import mutated_copy

SOURCE = "def total(items):\n    return sum(items)\n"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "calc.py").write_text(SOURCE, encoding="utf-8")
    (root / "README.md").write_text("# Proj\n", encoding="utf-8")
    return root


def _descriptor(**overrides) -> MutationDescriptor:
    fields = {
        "path": "pkg/calc.py",
        "start_line": 2,
        "end_line": 2,
        "replacement": "    return 0\n",
        "region_label": "pkg/calc.py#0",
    }
    fields.update(overrides)
    return MutationDescriptor(**fields)


def test_the_copy_carries_the_mutation(project: Path):
    with mutated_copy(project, _descriptor()) as root:
        assert (root / "pkg" / "calc.py").read_text(encoding="utf-8") == (
            "def total(items):\n    return 0\n"
        )


def test_the_original_is_unchanged(project: Path):
    with mutated_copy(project, _descriptor()):
        pass
    assert (project / "pkg" / "calc.py").read_text(encoding="utf-8") == SOURCE


def test_untouched_files_come_along(project: Path):
    with mutated_copy(project, _descriptor()) as root:
        assert (root / "README.md").read_text(encoding="utf-8") == "# Proj\n"


def test_the_copy_is_removed_afterwards(project: Path):
    with mutated_copy(project, _descriptor()) as root:
        recorded = root
        assert recorded.exists()
    assert not recorded.exists()


def test_the_copy_is_removed_even_when_the_caller_raises(project: Path):
    recorded: Path | None = None
    with pytest.raises(RuntimeError), mutated_copy(project, _descriptor()) as root:
        recorded = root
        raise RuntimeError("the test run blew up")
    assert recorded is not None and not recorded.exists()


def test_stale_bytecode_is_not_copied(project: Path):
    """A `__pycache__` whose source has just been mutated is the way an
    injected defect silently fails to take effect."""
    cache = project / "pkg" / "__pycache__"
    cache.mkdir()
    (cache / "calc.cpython-310.pyc").write_bytes(b"stale")
    with mutated_copy(project, _descriptor()) as root:
        assert not (root / "pkg" / "__pycache__").exists()


def test_a_file_the_project_does_not_have_is_reported(project: Path):
    with (
        pytest.raises(FileNotFoundError, match="not a file in the project"),
        mutated_copy(project, _descriptor(path="pkg/missing.py")),
    ):
        pass


def test_each_mutant_gets_its_own_copy(project: Path):
    """Two mutants must never be observed stacked on one another."""
    with (
        mutated_copy(project, _descriptor()) as first,
        mutated_copy(project, _descriptor(replacement="    return 1\n")) as second,
    ):
        assert first != second
        assert "return 0" in (first / "pkg" / "calc.py").read_text(encoding="utf-8")
        assert "return 1" in (second / "pkg" / "calc.py").read_text(encoding="utf-8")
