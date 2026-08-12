"""Surrounding-code retrieval (M2.2, §12 autonomous gathering / §17 cost).

For each changed code region, retrieve the enclosing definition (the innermost
function/class/method containing a changed line) and its direct in-repo call
sites, via Python AST — no LLM, this is structural. A `RetrievalBudget` bounds
breadth (files scanned, call sites per definition); when a cap is hit the
result is flagged truncated rather than silently dropping context (§3.2
decision, #75).

Caller matching is name-based (a call `foo(...)` / `obj.foo(...)` matches a
changed definition named `foo`) — a retrieval heuristic that surfaces
candidates; precision is a later concern (M3/M5), not retrieval's.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Literal

from pydantic import Field

from acceptance.model_base import PersistableModel
from acceptance.review_state import ChangeSet


class RetrievalBudget(PersistableModel):
    max_files_scanned: int = 200
    max_call_sites_per_definition: int = 20


class CodeDefinition(PersistableModel):
    qualname: str
    kind: Literal["function", "async_function", "class", "method"]
    file: str
    start_line: int
    end_line: int
    source: str


class CallSite(PersistableModel):
    file: str
    line: int
    source_line: str
    in_definition: str | None = None  # qualname of the enclosing definition, if any


class CodeContext(PersistableModel):
    definition: CodeDefinition
    call_sites: list[CallSite] = Field(default_factory=list)
    call_sites_truncated: bool = False


class RetrievalResult(PersistableModel):
    contexts: list[CodeContext] = Field(default_factory=list)
    files_scanned: int = 0
    files_scanned_truncated: bool = False


_DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

# Vendored / generated directories are never in-repo callers, and scanning them
# would waste the budget (they typically dwarf the source tree). Skipped.
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


def changed_definitions(repo: Path, change_set: ChangeSet) -> list[CodeDefinition]:
    """The innermost function/class/method enclosing each changed line, across
    every changed source file — the structural anchor both for surrounding-code
    retrieval (this module) and test discovery (evidence/discovery.py, M4.1),
    which reuses this to find the symbols a candidate test should reference."""
    definitions: dict[str, CodeDefinition] = {}
    for file_change in change_set.files:
        if file_change.category != "source" or file_change.status == "deleted":
            continue
        source = _read(repo / file_change.path)
        if source is None:
            continue
        module = _parse(source)
        if module is None:
            continue
        index = _index_definitions(module, file_change.path, source)
        for hunk in file_change.hunks:
            changed_lines = range(hunk.new_start, hunk.new_start + max(hunk.new_lines, 1))
            enclosing = _innermost_enclosing(index, changed_lines)
            if enclosing is not None:
                definitions[enclosing.qualname] = enclosing
    return list(definitions.values())


def retrieve_context(
    repo: Path, change_set: ChangeSet, budget: RetrievalBudget | None = None
) -> RetrievalResult:
    """Retrieve enclosing definitions of changed regions and their callers."""
    budget = budget or RetrievalBudget()

    definitions = {defn.qualname: defn for defn in changed_definitions(repo, change_set)}
    target_names = {defn.qualname.rsplit(".", 1)[-1]: defn for defn in definitions.values()}
    call_sites: dict[str, list[CallSite]] = {q: [] for q in definitions}
    truncated: dict[str, bool] = {q: False for q in definitions}

    files_scanned, files_truncated = _scan_callers(
        repo, target_names, call_sites, truncated, budget
    )

    contexts = [
        CodeContext(
            definition=defn,
            call_sites=call_sites[qualname],
            call_sites_truncated=truncated[qualname],
        )
        for qualname, defn in definitions.items()
    ]
    return RetrievalResult(
        contexts=contexts,
        files_scanned=files_scanned,
        files_scanned_truncated=files_truncated,
    )


def _scan_callers(
    repo: Path,
    target_names: dict[str, CodeDefinition],
    call_sites: dict[str, list[CallSite]],
    truncated: dict[str, bool],
    budget: RetrievalBudget,
) -> tuple[int, bool]:
    files = sorted(
        path
        for path in repo.rglob("*.py")
        if not (_EXCLUDED_DIRS & set(path.relative_to(repo).parts[:-1]))
    )
    files_truncated = len(files) > budget.max_files_scanned
    files_scanned = 0
    for path in files[: budget.max_files_scanned]:
        source = _read(path)
        if source is None:
            continue
        module = _parse(source)
        if module is None:
            continue
        files_scanned += 1
        rel = str(path.relative_to(repo))
        source_lines = source.splitlines()
        for call in _iter_calls(module):
            name = _call_name(call.node)
            defn = target_names.get(name)
            if defn is None:
                continue
            qualname = defn.qualname
            if len(call_sites[qualname]) >= budget.max_call_sites_per_definition:
                truncated[qualname] = True
                continue
            line = call.node.lineno
            call_sites[qualname].append(
                CallSite(
                    file=rel,
                    line=line,
                    source_line=source_lines[line - 1].strip() if line <= len(source_lines) else "",
                    in_definition=call.enclosing,
                )
            )
    return files_scanned, files_truncated


class _IndexedDef:
    def __init__(self, node: ast.AST, qualname: str, kind: str):
        self.node = node
        self.qualname = qualname
        self.kind = kind


def _index_definitions(module: ast.Module, file: str, source: str) -> list[CodeDefinition]:
    """All definitions in a module, with qualnames tracking nesting."""
    lines = source.splitlines()
    results: list[CodeDefinition] = []

    def visit(node: ast.AST, prefix: str, inside_class: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _DEF_NODES):
                qualname = f"{prefix}.{child.name}" if prefix else child.name
                kind = _kind(child, inside_class)
                end = getattr(child, "end_lineno", child.lineno)
                results.append(
                    CodeDefinition(
                        qualname=qualname,
                        kind=kind,
                        file=file,
                        start_line=child.lineno,
                        end_line=end,
                        source="\n".join(lines[child.lineno - 1 : end]),
                    )
                )
                visit(child, qualname, isinstance(child, ast.ClassDef))

    visit(module, "", False)
    return results


def _innermost_enclosing(
    definitions: list[CodeDefinition], changed_lines: range
) -> CodeDefinition | None:
    """The smallest-range definition that contains any of the changed lines."""
    candidates = [
        d for d in definitions if any(d.start_line <= line <= d.end_line for line in changed_lines)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda d: d.end_line - d.start_line)


class _Call:
    def __init__(self, node: ast.Call, enclosing: str | None):
        self.node = node
        self.enclosing = enclosing


def _iter_calls(module: ast.Module) -> list[_Call]:
    """Every call in the module, tagged with its enclosing definition qualname."""
    calls: list[_Call] = []

    def visit(node: ast.AST, enclosing: str | None, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Call):
                calls.append(_Call(child, enclosing))
            if isinstance(child, _DEF_NODES):
                qualname = f"{prefix}.{child.name}" if prefix else child.name
                visit(child, qualname, qualname)
            else:
                visit(child, enclosing, prefix)

    visit(module, None, "")
    return calls


def _call_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _kind(node: ast.AST, inside_class: bool) -> str:
    if isinstance(node, ast.ClassDef):
        return "class"
    if isinstance(node, ast.AsyncFunctionDef):
        return "async_function"
    return "method" if inside_class else "function"


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
