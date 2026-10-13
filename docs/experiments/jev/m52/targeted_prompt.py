"""Targeted code context for Jev: what a pre-built index of the code could supply.

The same shape for every case, whatever the file sizes:

- the edited code: the innermost function containing the edited line (with
  its class header when it is a method), from the mutated file, edited line(s)
  marked; the top-level statement instead when the edit is not in a function;
- the test: its file's import lines, the test function (with its class header),
  and the definitions of fixtures and helpers it names, found in the test file
  or a ``conftest.py`` on its path;
- called code: for every name the test calls (``f(...)`` or ``x.f(...)``), its
  definition in the project's non-test source when the name is defined in at
  most ``MAX_DEFS`` places. Names defined more often are skipped as ambiguous.

Bounded by ``BUDGET`` estimated tokens (``context_prompt.est``); definitions
that do not fit are dropped and recorded. Every inclusion and every drop is
returned in ``Targeted.included`` / ``Targeted.skipped``.
"""

from __future__ import annotations

import ast
import functools
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import agent_judge
import prompts
from context_prompt import (
    FAILS_SITUATION,
    MARK,
    REACH_QUESTION,
    REACH_SITUATION,
    _mutated_lines,
    est,
)
from run_jev_framing import ONE_QUESTION

BUDGET = 12_000
MAX_DEFS = 2
MAX_DEF_LINES = 120
SKIP_DIRS = {"test", "tests", "docs", "doc", "devscripts", "build", ".git", "__pycache__"}


@dataclass
class Targeted:
    edited: str
    test: str
    called: str
    included: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    # repo-relative path -> list of 1-based inclusive spans sent
    spans: dict[str, list[tuple[int, int]]] = field(default_factory=dict)


def _defs(tree: ast.AST):
    """(name, node, class_node_or_None) for every function and class."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            yield node.name, node, None
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield child.name, child, node
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node, None


@functools.cache
def _index(root: Path) -> dict[str, list[tuple[str, int, int, int | None]]]:
    """name -> [(path, start, end, class_line)] over the project's non-test source."""
    out: dict[str, list] = {}
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]) or rel.name.startswith("test"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        seen = set()
        for name, node, cls in _defs(tree):
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            key = (name, start)
            if key in seen:
                continue
            seen.add(key)
            out.setdefault(name, []).append(
                (str(rel), start, node.end_lineno, cls.lineno if cls else None)
            )
    return out


def _span_text(lines: list[str], start: int, end: int, cls_line: int | None) -> str:
    body = lines[start - 1 : end]
    if len(body) > MAX_DEF_LINES:
        body = body[:MAX_DEF_LINES] + ["    ... (truncated)"]
    head = [lines[cls_line - 1], "    ..."] if cls_line else []
    return "\n".join(head + body)


def _edited(case) -> tuple[str, tuple[int, int]]:
    lines = _mutated_lines(case)
    tree = ast.parse("\n".join(ln.replace(MARK, "") for ln in lines))
    line = case.edit.start_line
    best = None
    for _, node, cls in _defs(tree):
        if isinstance(node, ast.ClassDef):
            continue
        start = min([node.lineno] + [d.lineno for d in node.decorator_list])
        if start <= line <= node.end_lineno and (best is None or start >= best[0]):
            best = (start, node.end_lineno, cls.lineno if cls else None)
    if best is None:
        for node in tree.body:  # module-level edit: its top-level statement
            if node.lineno <= line <= node.end_lineno:
                best = (node.lineno, node.end_lineno, None)
                break
    start, end, cls_line = best
    head = [lines[cls_line - 1], "    ..."] if cls_line else []
    return "\n".join(head + lines[start - 1 : end]), (start, end)


def _parse(source: str) -> ast.Module:
    """Parse a test that may be an indented method.

    Dedenting fails when the body holds a multi-line string at column 0, so
    fall back to wrapping the source in a class.
    """
    try:
        return ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return ast.parse("class _Wrapper:\n" + source)


def _called_names(source: str) -> list[str]:
    tree = _parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = (
                f.id
                if isinstance(f, ast.Name)
                else f.attr
                if isinstance(f, ast.Attribute)
                else None
            )
            if name and name not in names:
                names.append(name)
    return names


def _param_names(source: str) -> list[str]:
    tree = _parse(source)
    fn = next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    return [a.arg for a in fn.args.args if a.arg not in ("self", "cls")]


def build(case) -> Targeted:
    root = agent_judge.PROJECTS / f"{case.project}-{case.bug_id}"
    test_path = case.test_id.split("::")[0]
    edited, edited_span = _edited(case)
    t = Targeted(edited=edited, test="", called="")
    t.spans.setdefault(case.edit.path, []).append(edited_span)
    t.included.append(f"edited: {case.edit.path}:{edited_span[0]}-{edited_span[1]}")

    # The test: imports, class header, the test, and its named fixtures/helpers.
    test_text = (root / test_path).read_text(encoding="utf-8", errors="replace")
    test_lines = test_text.splitlines()
    test_tree = ast.parse(test_text)
    imports = [
        "\n".join(test_lines[n.lineno - 1 : n.end_lineno])
        for n in test_tree.body
        if isinstance(n, (ast.Import, ast.ImportFrom))
    ]
    local: dict[str, tuple[str, list[str], ast.AST]] = {}
    conftests = [root / p / "conftest.py" for p in [*Path(test_path).parents]]
    for path in [root / test_path, *[c for c in conftests if c.is_file()]]:
        text = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and not node.name.startswith("test"):
                local.setdefault(node.name, (str(path.relative_to(root)), text.splitlines(), node))
    wanted = _param_names(case.test_source) + _called_names(case.test_source)
    helpers = []
    for name in wanted:
        if name in local:
            rel, lines, node = local[name]
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            helpers.append(_span_text(lines, start, node.end_lineno, None))
            t.spans.setdefault(rel, []).append((start, node.end_lineno))
            t.included.append(f"test helper: {rel}:{start} {name}")
    cls_header = ""
    parts = case.test_id.split("::")[1:]
    if len(parts) == 2:
        cls = next(
            (n for n in test_tree.body if isinstance(n, ast.ClassDef) and n.name == parts[0]), None
        )
        if cls is not None:
            cls_header = test_lines[cls.lineno - 1] + "\n    ...\n"
    t.test = "\n".join(imports) + "\n\n" + "\n\n".join(helpers + [cls_header + case.test_source])

    # Called code from the project source.
    index = _index(root)
    used = est(t.edited) + est(t.test)
    chunks = []
    names = _called_names(case.test_source)
    for helper in helpers:
        names += [n for n in _called_names(helper) if n not in names]
    for name in names:
        defs = index.get(name, [])
        if not defs:
            continue
        if len(defs) > MAX_DEFS:
            t.skipped.append(f"{name}: ambiguous ({len(defs)} definitions)")
            continue
        for rel, start, end, cls_line in defs:
            if rel == case.edit.path and start <= edited_span[0] and end >= edited_span[1]:
                continue  # already sent as the edited code
            lines = (root / rel).read_text(encoding="utf-8", errors="replace").splitlines()
            text = f"# {rel}\n" + _span_text(lines, start, end, cls_line)
            if used + est(text) > BUDGET:
                t.skipped.append(f"{name}: over budget ({rel}:{start}, ~{est(text)} tokens)")
                continue
            used += est(text)
            chunks.append(text)
            t.spans.setdefault(rel, []).append((start, min(end, start + MAX_DEF_LINES - 1)))
            t.included.append(f"called: {rel}:{start} {name}")
    t.called = "\n\n".join(chunks)
    return t


def reach_body(case) -> dict:
    t = build(case)
    return {
        "model": "jev-latest",
        "state": {
            "situation": REACH_SITUATION,
            "test": t.test,
            "test_name": case.test_id.split("::", 1)[1],
            "code": t.edited,
            "code_the_test_calls": t.called,
        },
        "questions": REACH_QUESTION,
    }


def fails_body(case) -> dict:
    t = build(case)
    return {
        "model": "jev-latest",
        "state": {
            "situation": FAILS_SITUATION,
            "change_request": prompts.commit_message(case),
            "test": t.test,
            "test_name": case.test_id.split("::", 1)[1],
            "code": t.edited,
            "code_the_test_calls": t.called,
            "edit": f"original: {case.edit.original.strip()}\nnow: {case.edit.replacement.strip()}",
        },
        "questions": ONE_QUESTION,
    }
