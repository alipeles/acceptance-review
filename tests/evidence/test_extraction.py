"""M5.1 acceptance: per-test structural extraction — for archetype #5 the
analyzer identifies that the expected value is produced by the same production
function (circular provenance) — plus unit coverage of the other extracted
fields and the non-circular (independent expected value) case.

Extraction is pure AST (no model call), so these assert real structural
judgments directly rather than injected responses. Tests write real repos so
the extractor can see file-level imports (the production-symbol signal).
"""

from pathlib import Path

from acceptance.change.diff import extract_change_set
from acceptance.evidence.discovery import discover_tests
from acceptance.evidence.extraction import extract_test_evidence
from acceptance.evidence.mapping import MappingResult, TestMapping
from acceptance.review_state import ChangeSet, DiffHunk, FileChange


def _hunk(new_lines: int) -> DiffHunk:
    return DiffHunk(
        header=f"@@ -1,{new_lines} +1,{new_lines} @@",
        old_start=1,
        old_lines=new_lines,
        new_start=1,
        new_lines=new_lines,
        content="",
    )


def _change_set(path: str, new_lines: int) -> ChangeSet:
    return ChangeSet(
        base_revision="base",
        head_revision="head",
        files=[
            FileChange(path=path, status="modified", category="source", hunks=[_hunk(new_lines)])
        ],
    )


def _mapping(*pairs: tuple[str, list[str]]) -> MappingResult:
    return MappingResult(
        mappings=[TestMapping(test_id=t, obligation_ids=o, rationale=".") for t, o in pairs],
        unmapped_obligation_ids=[],
    )


def _extract(repo: Path, change_set: ChangeSet, *mapped: tuple[str, list[str]]):
    discovered = discover_tests(repo, change_set)
    return extract_test_evidence(repo, discovered.tests, change_set, _mapping(*mapped))


# --- unit-level: hand-built repos (no git needed) ---


def test_circular_expected_value_is_detected(tmp_path):
    (tmp_path / "orders.py").write_text(
        "def _apply_tax(subtotal, tax_rate):\n"
        "    return subtotal * (1 + tax_rate)\n\n\n"
        "def order_total(subtotal, tax_rate):\n"
        "    return round(_apply_tax(subtotal, tax_rate), 2)\n"
    )
    (tmp_path / "test_orders.py").write_text(
        "from orders import _apply_tax, order_total\n\n\n"
        "def test_total():\n"
        "    subtotal, tax_rate = 100.0, 0.08\n"
        "    expected = round(_apply_tax(subtotal, tax_rate), 2)\n"
        "    assert order_total(subtotal, tax_rate) == expected\n"
    )
    change_set = _change_set("orders.py", new_lines=6)

    evidence = _extract(tmp_path, change_set, ("test_orders.py::test_total", ["add-tax"]))

    ev = next(e for e in evidence if e.identifier == "test_orders.py::test_total")
    assert ev.expected_value_provenance is not None
    assert ev.expected_value_provenance.startswith("Circular")
    assert "_apply_tax" in ev.expected_value_provenance
    assert ev.mapped_obligations == ["add-tax"]


def test_independent_literal_expected_value_is_not_circular(tmp_path):
    (tmp_path / "orders.py").write_text(
        "def order_total(subtotal, tax_rate):\n    return round(subtotal * (1 + tax_rate), 2)\n"
    )
    (tmp_path / "test_orders.py").write_text(
        "from orders import order_total\n\n\n"
        "def test_total():\n"
        "    assert order_total(100.0, 0.08) == 108.0\n"
    )
    change_set = _change_set("orders.py", new_lines=2)

    evidence = _extract(tmp_path, change_set, ("test_orders.py::test_total", ["add-tax"]))

    ev = next(e for e in evidence if e.identifier == "test_orders.py::test_total")
    assert ev.expected_value_provenance is not None
    assert ev.expected_value_provenance.startswith("Independent")


def test_extraction_captures_assertions_inputs_fixtures_and_mocks(tmp_path):
    (tmp_path / "svc.py").write_text(
        "def charge(amount, gateway):\n    return gateway.pay(amount)\n"
    )
    (tmp_path / "test_svc.py").write_text(
        "from unittest.mock import Mock\n"
        "from svc import charge\n\n\n"
        "def test_charge(monkeypatch):\n"
        "    gateway = Mock()\n"
        "    assert charge(50, gateway) == gateway.pay.return_value\n"
    )
    change_set = _change_set("svc.py", new_lines=2)

    evidence = _extract(tmp_path, change_set, ("test_svc.py::test_charge", ["pay"]))

    ev = next(e for e in evidence if e.identifier == "test_svc.py::test_charge")
    assert ev.fixtures == ["monkeypatch"]
    assert "Mock" in ev.mocks
    assert any("charge(50, gateway)" in a for a in ev.assertions)
    assert "charge(50, gateway)" in ev.inputs


def test_class_method_is_extracted(tmp_path):
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\n\nclass TestC:\n    def test_it(self):\n        assert f() == 1\n"
    )
    change_set = _change_set("mod.py", new_lines=2)

    evidence = _extract(tmp_path, change_set, ("test_mod.py::TestC::test_it", []))

    ev = next(e for e in evidence if e.identifier == "test_mod.py::TestC::test_it")
    assert ev.fixtures == []  # self is dropped
    assert any("f()" in a for a in ev.assertions)


# --- acceptance: real archetype #5 via the full discover -> map -> extract path ---

ARCHETYPES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"


def test_archetype_5_circular_provenance_is_identified(tmp_path):
    from acceptance.benchmark.fixtures import materialize_archetype

    fixture = materialize_archetype(
        ARCHETYPES_DIR / "05-circular-expected-result", tmp_path / "repo"
    )
    repo = fixture.repo_path
    change_set = extract_change_set(repo, fixture.base_sha, fixture.head_sha)

    discovered = discover_tests(repo, change_set)
    test_id = "test_orders.py::test_total_applies_tax"
    assert test_id in {t.test_id for t in discovered.tests}

    mapping = _mapping((test_id, ["add-tax", "round-2"]))
    evidence = extract_test_evidence(repo, discovered.tests, change_set, mapping)

    ev = next(e for e in evidence if e.identifier == test_id)
    assert ev.expected_value_provenance is not None
    assert ev.expected_value_provenance.startswith("Circular")
    assert "_apply_tax" in ev.expected_value_provenance
