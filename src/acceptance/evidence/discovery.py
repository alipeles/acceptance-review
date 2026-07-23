"""Test discovery (M4.1, §9.1 "candidate tests").

Collects the tests relevant to a change set: every added/modified test, plus
existing (untouched) tests connected to a changed symbol — by call graph,
non-call reference, import, or naming — via Python AST, no LLM call (this is
structural, like M2's diff/context extraction). This produces the *candidate*
set M4.2 maps to obligations and M5 analyzes test-by-test; it does not judge
test strength or relevance beyond "this test touches changed code."

Changed-symbol names come from `change/context.py`'s `changed_definitions` —
the same enclosing-definition extraction M2.2 uses for surrounding-code
retrieval, reused here rather than recomputed. Existing-test-file discovery
scans the repo by pytest's own naming convention (`test_*.py`/`*_test.py`),
excluding vendored/generated directories (the same denylist as
change/context.py's caller scan — kept local here rather than imported, since
these are small, stable utilities and the two scans walk the tree for
different purposes).
"""

from __future__ import annotations

import ast
from enum import Enum
from pathlib import Path

from pydantic import Field

from acceptance.change.context import changed_definitions
from acceptance.model_base import PersistableModel
from acceptance.review_state import ChangeSet

_EXCLUDED_DIRS = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    "node_modules",
    "build",
    "dist",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "site-packages",
    ".eggs",
}


class TestDiscoveryBudget(PersistableModel):
    __test__ = False  # not a pytest test class; matches TestEvidence's precedent

    max_files_scanned: int = 500


class DiscoveryReason(str, Enum):
    ADDED_OR_MODIFIED = "added_or_modified"
    CALLS_CHANGED_SYMBOL = "calls_changed_symbol"
    REFERENCES_CHANGED_SYMBOL = "references_changed_symbol"
    IMPORTS_CHANGED_MODULE = "imports_changed_module"
    NAME_MATCHES_SYMBOL = "name_matches_symbol"


class DiscoveredTest(PersistableModel):
    """A candidate test, and why it was discovered — never zero reasons."""

    test_id: str  # pytest nodeid: "path/test_x.py::test_fn" or "...::TestC::test_m"
    file: str
    reasons: list[DiscoveryReason] = Field(default_factory=list)


class TestDiscoveryResult(PersistableModel):
    __test__ = False  # not a pytest test class; matches TestEvidence's precedent

    tests: list[DiscoveredTest] = Field(default_factory=list)
    files_scanned: int = 0
    files_scanned_truncated: bool = False


class _TestItem:
    def __init__(self, node: ast.AST, name: str, class_name: str | None):
        self.node = node
        self.name = name
        self.class_name = class_name


def _test_items(module: ast.Module) -> list[_TestItem]:
    """Pytest-collectible test functions: top-level `test_*` functions, and
    `test_*` methods on a top-level `Test*` class — pytest's own default
    collection convention (`python_functions`/`python_classes`)."""
    items: list[_TestItem] = []
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test_"
        ):
            items.append(_TestItem(node, node.name, None))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for child in node.body:
                if isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and child.name.startswith("test_"):
                    items.append(_TestItem(child, child.name, node.name))
    return items


def _node_id(path: str, item: _TestItem) -> str:
    if item.class_name:
        return f"{path}::{item.class_name}::{item.name}"
    return f"{path}::{item.name}"


def _is_test_file(path: Path) -> bool:
    name = path.name
    return name.startswith("test_") or name.endswith("_test.py")


def _names_called(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _names_referenced(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return names


def _imported_module_stems(module: ast.Module) -> set[str]:
    stems: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            for alias in node.names:
                stems.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            stems.add(node.module.split(".")[0])
    return stems


def _changed_symbol_names(repo: Path, change_set: ChangeSet) -> set[str]:
    return {defn.qualname.rsplit(".", 1)[-1] for defn in changed_definitions(repo, change_set)}


def _changed_module_stems(change_set: ChangeSet) -> set[str]:
    return {
        Path(f.path).stem
        for f in change_set.files
        if f.category == "source" and f.status != "deleted" and f.path.endswith(".py")
    }


def _added_or_modified_tests(repo: Path, change_set: ChangeSet) -> dict[str, DiscoveredTest]:
    discovered: dict[str, DiscoveredTest] = {}
    for file_change in change_set.files:
        if file_change.category != "test" or file_change.status == "deleted":
            continue
        source = _read(repo / file_change.path)
        module = _parse(source) if source is not None else None
        if module is None:
            continue
        for item in _test_items(module):
            test_id = _node_id(file_change.path, item)
            discovered[test_id] = DiscoveredTest(
                test_id=test_id,
                file=file_change.path,
                reasons=[DiscoveryReason.ADDED_OR_MODIFIED],
            )
    return discovered


def _existing_test_files(repo: Path, budget: TestDiscoveryBudget) -> tuple[list[Path], bool]:
    files = sorted(
        path
        for path in repo.rglob("*.py")
        if _is_test_file(path)
        and not (_EXCLUDED_DIRS & set(path.relative_to(repo).parts[:-1]))
    )
    return files[: budget.max_files_scanned], len(files) > budget.max_files_scanned


def discover_tests(
    repo: Path, change_set: ChangeSet, budget: TestDiscoveryBudget | None = None
) -> TestDiscoveryResult:
    """Discover the tests relevant to a change set."""
    budget = budget or TestDiscoveryBudget()

    discovered = _added_or_modified_tests(repo, change_set)
    already_covered = {f.path for f in change_set.files}

    symbol_names = _changed_symbol_names(repo, change_set)
    module_stems = _changed_module_stems(change_set)

    files, files_truncated = _existing_test_files(repo, budget)
    files_scanned = 0
    for path in files:
        rel = str(path.relative_to(repo))
        if rel in already_covered:
            continue  # added/modified tests are handled above, with their own reason
        source = _read(path)
        module = _parse(source) if source is not None else None
        if module is None:
            continue
        files_scanned += 1

        module_import_hit = bool(_imported_module_stems(module) & module_stems)
        for item in _test_items(module):
            called = _names_called(item.node) & symbol_names
            touched_only = (_names_referenced(item.node) & symbol_names) - called

            reasons = []
            if called:
                reasons.append(DiscoveryReason.CALLS_CHANGED_SYMBOL)
            if touched_only:
                reasons.append(DiscoveryReason.REFERENCES_CHANGED_SYMBOL)
            if module_import_hit:
                reasons.append(DiscoveryReason.IMPORTS_CHANGED_MODULE)
            if any(name in item.name for name in symbol_names):
                reasons.append(DiscoveryReason.NAME_MATCHES_SYMBOL)

            if reasons:
                test_id = _node_id(rel, item)
                discovered[test_id] = DiscoveredTest(test_id=test_id, file=rel, reasons=reasons)

    return TestDiscoveryResult(
        tests=sorted(discovered.values(), key=lambda t: t.test_id),
        files_scanned=files_scanned,
        files_scanned_truncated=files_truncated,
    )


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _parse(source: str) -> ast.Module | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None
