"""The targeted code Jev is shown about one pair (#385)."""

from __future__ import annotations

from pathlib import Path

from acceptance.defects.jev_context import MARK, CodeIndex, build_context
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.review_state import ChangeSet, Defect, DefectType, DiffHunk, FileChange

BILLING = """\
import math


def unrelated():
    return 0


class Invoice:
    def total(self, items):
        subtotal = sum(items)
        return round(subtotal * 1.2, 2)


def charge(amount):
    return amount
"""

HELPERS = """\
def make_items():
    return [1, 2]
"""

TEST = """\
from billing import Invoice
from tests.helpers_local import thing


def build():
    return [5, 5]


def test_total():
    assert Invoice().total(build()) == charge(12.0)
"""

TEST_SOURCE = """\
def test_total():
    assert Invoice().total(build()) == charge(12.0)
"""


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "billing.py").write_text(BILLING)
    (tmp_path / "helpers.py").write_text(HELPERS)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_billing.py").write_text(TEST)
    # A virtualenv's copy of a name must never count as the project's definition.
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "fake.py").write_text("def total():\n    return 1\n")
    return tmp_path


def _change_set(new_start: int, new_lines: int) -> ChangeSet:
    return ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="billing.py",
                status="modified",
                category="source",
                hunks=[
                    DiffHunk(
                        header="@@",
                        old_start=new_start,
                        old_lines=new_lines,
                        new_start=new_start,
                        new_lines=new_lines,
                        content="body",
                    )
                ],
            )
        ],
    )


def _defect() -> Defect:
    return Defect(
        id="d1",
        obligation_id="o1",
        type=DefectType.OTHER,
        description="tax is applied twice",
        code_refs=["billing.py#0"],
    )


def _test() -> DiscoveredTest:
    return DiscoveredTest(
        test_id="tests/test_billing.py::test_total",
        file="tests/test_billing.py",
        source=TEST_SOURCE,
    )


def test_the_defect_region_is_shown_inside_its_method_with_its_lines_marked(tmp_path):
    repo = _repo(tmp_path)
    # Line 11 is `return round(...)` inside Invoice.total.
    context = build_context(_defect(), _test(), _change_set(11, 1), CodeIndex(repo))
    assert "class Invoice:" in context.code
    assert "def total(self, items):" in context.code
    assert f"return round(subtotal * 1.2, 2){MARK}" in context.code
    assert f"subtotal = sum(items){MARK}" not in context.code
    assert "def unrelated" not in context.code


def test_the_test_comes_with_its_imports_and_the_helper_it_calls(tmp_path):
    context = build_context(_defect(), _test(), _change_set(11, 1), CodeIndex(_repo(tmp_path)))
    assert "from billing import Invoice" in context.test
    assert "def build():" in context.test
    assert context.test.rstrip().endswith("assert Invoice().total(build()) == charge(12.0)")


def test_called_code_comes_from_project_source_and_skips_what_was_already_shown(tmp_path):
    context = build_context(_defect(), _test(), _change_set(11, 1), CodeIndex(_repo(tmp_path)))
    # `total` is the defect's own method, already shown; the venv copy is not
    # project source, so it is not offered either.
    assert "fake.py" not in context.called
    assert "def total" not in context.called
    assert "def charge(amount):" in context.called
    assert "called: billing.py:14 charge" in context.included


def test_a_defect_naming_no_region_still_yields_a_context(tmp_path):
    defect = _defect().model_copy(update={"code_refs": []})
    context = build_context(defect, _test(), _change_set(11, 1), CodeIndex(_repo(tmp_path)))
    assert context.code == ""
    assert "def test_total" in context.test


def test_the_same_inputs_build_the_same_context(tmp_path):
    repo = _repo(tmp_path)
    first = build_context(_defect(), _test(), _change_set(10, 2), CodeIndex(repo))
    second = build_context(_defect(), _test(), _change_set(10, 2), CodeIndex(repo))
    assert (first.code, first.test, first.called) == (second.code, second.test, second.called)
