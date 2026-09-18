"""The collection gate: what the project's own pytest will actually admit.

`sandbox.py::collect_tests` is the fix for the failure that left #45's execution
tier completely inert. Test discovery walks the repository for test files;
pytest decides what is a test by its own rules, and an id it cannot collect
makes it exit with a usage error and run **nothing**. One archetype-fixture test
took all 341 candidate tests down with it.

Gate 2 run 3 reported this criterion as only partially supported and asked for
exactly this case. I verified the gate had **no test referencing it at all** —
the shape CLAUDE.md warns about, a helper the pipeline depends on that nothing
exercises.

These drive a real pytest against throwaway projects, so what is asserted is
what the project's own pytest does rather than what a stub was told to say.
"""

from __future__ import annotations

import pytest

from acceptance.execution.sandbox import SandboxConfig, collect_tests

_GOOD = "def test_ok():\n    assert True\n"
_BROKEN_IMPORT = (
    "import a_module_that_does_not_exist\n\n\ndef test_never_runs():\n    assert True\n"
)
_SYNTAX_ERROR = "def test_bad(:\n    pass\n"


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    return root


class TestWhatItAdmits:
    def test_a_collectable_test_is_admitted(self, project):
        (project / "test_a.py").write_text(_GOOD, encoding="utf-8")
        assert collect_tests(["test_a.py::test_ok"], project) == {"test_a.py::test_ok"}

    def test_an_id_no_file_backs_is_not_admitted(self, project):
        (project / "test_a.py").write_text(_GOOD, encoding="utf-8")
        admitted = collect_tests(["test_a.py::test_ok", "test_ghost.py::test_x"], project)
        assert admitted == {"test_a.py::test_ok"}

    def test_requesting_nothing_admits_nothing(self, project):
        assert collect_tests([], project) == set()


class TestOneBrokenFileDoesNotCostTheOthers:
    """The whole point of the gate. Before it, one uncollectable id made pytest
    exit with a usage error and run nothing, so every other candidate test was
    lost with it."""

    @pytest.mark.parametrize(
        ("name", "body"),
        [("test_broken_import.py", _BROKEN_IMPORT), ("test_syntax.py", _SYNTAX_ERROR)],
    )
    def test_the_good_test_survives_a_bad_file(self, project, name, body):
        (project / "test_good.py").write_text(_GOOD, encoding="utf-8")
        (project / name).write_text(body, encoding="utf-8")

        admitted = collect_tests(["test_good.py::test_ok", f"{name}::test_never_runs"], project)

        assert "test_good.py::test_ok" in admitted, (
            "one uncollectable file cost the collectable one, which is the failure "
            "this gate exists to prevent"
        )
        assert f"{name}::test_never_runs" not in admitted


class TestItReturnsRatherThanRaising:
    """The documented contract, which `establish_baseline` relies on: on any
    failure the answer is an empty set, which the caller reads as "nothing can
    be run here" and falls back to reading code."""

    def test_an_interpreter_that_does_not_exist_yields_nothing(self, project):
        (project / "test_a.py").write_text(_GOOD, encoding="utf-8")
        admitted = collect_tests(
            ["test_a.py::test_ok"],
            project,
            SandboxConfig(interpreter="/nonexistent/python"),
        )
        assert admitted == set()

    def test_a_project_that_is_not_a_directory_yields_nothing(self, tmp_path):
        missing = tmp_path / "not-a-project"
        assert collect_tests(["test_a.py::test_ok"], missing) == set()
