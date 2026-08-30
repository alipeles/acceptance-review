"""The pair prefilter excludes only what it can prove, and records what it excludes (#314).

The filter's whole value is in what it REFUSES to exclude. #314 says exclude only
on proof, and DR-312's resolved question 2 rules out the machinery that would
make most absences provable, so almost every pair survives. These tests pin both
halves: the one shape that is genuinely provable is excluded and recorded, and
each shape that merely LOOKS unreachable is judged anyway.

The negative cases matter more than the positive one. A wrong exclusion silently
un-covers a defect and produces a recommendation to write a test that already
exists (#250, #287), which is the failure #312 exists to remove.
"""

from __future__ import annotations

from pathlib import Path

from acceptance.defects.reachability import Pair, form_pairs, prefilter
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.review_state import ChangeSet, Defect, DiffHunk, FileChange, UnjudgedCause

_BILLING = '''\
def charge(monthly, days_used, days_in_month):
    """The defect lives here."""
    return monthly / 30 * days_used
'''


def _repo(tmp_path: Path, tests: dict[str, str], extra: dict[str, str] | None = None) -> Path:
    (tmp_path / "billing.py").write_text(_BILLING, encoding="utf-8")
    for path, source in (extra or {}).items():
        (tmp_path / path).write_text(source, encoding="utf-8")
    for path, source in tests.items():
        (tmp_path / path).write_text(source, encoding="utf-8")
    return tmp_path


def _change_set() -> ChangeSet:
    return ChangeSet(
        base_revision="base",
        head_revision="head",
        files=[
            FileChange(
                path="billing.py",
                status="modified",
                category="source",
                hunks=[
                    DiffHunk(
                        header="@@ -1,3 +1,3 @@",
                        old_start=1,
                        old_lines=3,
                        new_start=1,
                        new_lines=3,
                        content="+    return monthly / 30 * days_used\n",
                    )
                ],
            )
        ],
    )


def _defect(code_refs: list[str] | None = None) -> Defect:
    return Defect(
        id="d-hard-coded-thirty",
        obligation_id="daily-rate",
        type="other",
        description="The daily rate divides by a hard-coded 30 rather than days_in_month.",
        code_refs=["billing.py#0"] if code_refs is None else code_refs,
    )


def _test(test_id: str, file: str, source: str) -> DiscoveredTest:
    return DiscoveredTest(test_id=test_id, file=file, reasons=[], source=source)


def test_excludes_and_records_the_one_provable_shape(tmp_path):
    """A test that imports nothing first-party, takes no fixture and names nothing
    the defect's file defines has no path to the defect, and is excluded."""
    source = "def test_unrelated():\n    assert 1 + 1 == 2\n"
    repo = _repo(tmp_path, {"test_arithmetic.py": source})
    pair = Pair(
        _defect(), _test("test_arithmetic.py::test_unrelated", "test_arithmetic.py", source)
    )

    judged, excluded = prefilter([pair], repo, _change_set())

    assert judged == []
    assert len(excluded) == 1
    # Both ids and a reason, per #314: an exclusion nothing can see is
    # indistinguishable from a verdict of `survives`.
    assert excluded[0].defect_id == "d-hard-coded-thirty"
    assert excluded[0].test_id == "test_arithmetic.py::test_unrelated"
    assert "billing.py" in excluded[0].reason
    assert excluded[0].reason.strip() != ""
    # Proved unreachable, not shed by the judge. The two causes have opposite
    # remedies, so a filter that recorded them alike would hide one behind the
    # other.
    assert excluded[0].cause is UnjudgedCause.PREFILTERED


def test_judges_a_test_that_reaches_the_defect_through_a_helper_module(tmp_path):
    """THE case the filter must not get wrong.

    The test references no changed name and imports no changed module — the
    one-hop signal `discovery.py` computes is entirely absent — and it still
    fails on the defect, because the helper it calls calls the defective code.
    A filter that excluded this would lose a real kill silently.
    """
    helper = "from billing import charge\n\n\ndef make_invoice():\n    return charge(300, 15, 31)\n"
    source = (
        "from helpers import make_invoice\n\n\ndef test_total():\n    assert make_invoice() > 0\n"
    )
    repo = _repo(tmp_path, {"test_invoice.py": source}, extra={"helpers.py": helper})
    pair = Pair(_defect(), _test("test_invoice.py::test_total", "test_invoice.py", source))

    judged, excluded = prefilter([pair], repo, _change_set())

    assert excluded == []
    assert [p.key for p in judged] == [("d-hard-coded-thirty", "test_invoice.py::test_total")]


def test_judges_a_test_that_takes_a_fixture(tmp_path):
    """A parameter is a fixture request, and a fixture can call anything —
    including the defect's code — without the test module importing it."""
    source = "def test_with_fixture(invoice):\n    assert invoice > 0\n"
    repo = _repo(tmp_path, {"test_fixture.py": source})
    pair = Pair(_defect(), _test("test_fixture.py::test_with_fixture", "test_fixture.py", source))

    judged, excluded = prefilter([pair], repo, _change_set())

    assert excluded == []
    assert len(judged) == 1


def test_judges_when_the_module_imports_dynamically(tmp_path):
    """`importlib` can reach a module no import statement names, so nothing
    about that module's reach is provable."""
    source = (
        "import importlib\n\n\ndef test_dynamic():\n"
        "    assert importlib.import_module('billing') is not None\n"
    )
    repo = _repo(tmp_path, {"test_dynamic.py": source})
    pair = Pair(_defect(), _test("test_dynamic.py::test_dynamic", "test_dynamic.py", source))

    judged, excluded = prefilter([pair], repo, _change_set())

    assert excluded == []
    assert len(judged) == 1


def test_judges_when_the_defect_implicates_no_file(tmp_path):
    """With no implicated region, nothing is known about where the defect lives,
    so no absence can be proved."""
    source = "def test_unrelated():\n    assert 1 + 1 == 2\n"
    repo = _repo(tmp_path, {"test_arithmetic.py": source})
    pair = Pair(
        _defect(code_refs=[]),
        _test("test_arithmetic.py::test_unrelated", "test_arithmetic.py", source),
    )

    judged, excluded = prefilter([pair], repo, _change_set())

    assert excluded == []
    assert len(judged) == 1


def test_judges_a_test_that_names_something_the_defects_file_defines(tmp_path):
    """Referencing a changed definition is a direct path, whatever else the
    module does or does not import."""
    source = "def test_charge_shape():\n    charge = 1\n    assert charge == 1\n"
    repo = _repo(tmp_path, {"test_names.py": source})
    pair = Pair(_defect(), _test("test_names.py::test_charge_shape", "test_names.py", source))

    judged, excluded = prefilter([pair], repo, _change_set())

    assert excluded == []
    assert len(judged) == 1


def test_judges_when_the_module_imports_relatively(tmp_path):
    """A relative import names a sibling this filter cannot resolve without
    following the edge, which is the transitive step #314 puts out of scope."""
    source = "from . import helpers\n\n\ndef test_relative():\n    assert helpers is not None\n"
    repo = _repo(tmp_path, {"test_relative.py": source}, extra={"helpers.py": "x = 1\n"})
    pair = Pair(_defect(), _test("test_relative.py::test_relative", "test_relative.py", source))

    judged, excluded = prefilter([pair], repo, _change_set())

    assert excluded == []
    assert len(judged) == 1


def test_pairs_are_formed_in_a_fixed_order(tmp_path):
    """The order reaches the request, so it cannot depend on how the filesystem
    was walked or a recorded run stops replaying."""
    source = "def test_a():\n    assert True\n"
    first = _defect()
    second = Defect(
        id="a-earlier-defect", obligation_id="daily-rate", type="other", description="another"
    )
    tests = [
        _test("test_z.py::test_a", "test_z.py", source),
        _test("test_a.py::test_a", "test_a.py", source),
    ]

    pairs = form_pairs([first, second], tests)

    assert [pair.key for pair in pairs] == [
        ("a-earlier-defect", "test_a.py::test_a"),
        ("a-earlier-defect", "test_z.py::test_a"),
        ("d-hard-coded-thirty", "test_a.py::test_a"),
        ("d-hard-coded-thirty", "test_z.py::test_a"),
    ]
