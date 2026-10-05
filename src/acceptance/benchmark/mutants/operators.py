"""Fixed mutation operators, applied to named lines of a Python file (#372).

Each operator makes one mechanical, single-line edit, and its description is
written from the edit itself, so it cannot claim more than was injected. That is
the property #372 needs and the checker's model-written edits lack (DR-171's
audits: 52–60% introduced the defect they named).

Only nodes that start and end on one line are mutated, so an edit is a
whole-line splice and can be shown as one `-`/`+` pair. Column offsets from
`ast` are UTF-8 byte offsets, which is why splicing works on encoded bytes.

Generation is deterministic: the same source and line set always yield the same
mutants in the same order.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from acceptance.benchmark.mutants.labels import MutantEdit

__all__ = ["Mutant", "generate_mutants", "implementation_hunk"]

#: Each comparison operator's negation, as source tokens.
_COMPARE_FLIP = {
    "==": "!=",
    "!=": "==",
    "<": ">=",
    ">=": "<",
    ">": "<=",
    "<=": ">",
    "is not": "is",
    "is": "is not",
    "not in": "in",
    "in": "not in",
}
_COMPARE_TOKEN = re.compile(r"==|!=|<=|>=|<|>|\bis\s+not\b|\bnot\s+in\b|\bis\b|\bin\b")

#: Hunks longer than this are cut to a window around the edited line, so a case
#: stays within the state budget a judge is given.
_MAX_HUNK_LINES = 60
_WINDOW = 15

#: Maps a node's original source text to its replacement, or None to skip.
Rewrite = Callable[[str], "str | None"]
#: Maps (original text, replacement text) to the clause describing the edit.
Explain = Callable[[str, str], str]


@dataclass(frozen=True)
class Mutant:
    edit: MutantEdit
    description: str
    mutated_source: str


@dataclass(frozen=True)
class _Application:
    operator: str
    node: ast.AST
    rewrite: Rewrite
    explain: Explain


def generate_mutants(source: str, path: str, lines: set[int]) -> list[Mutant]:
    """Every operator application whose node lies on one of `lines`.

    Mutants that do not parse, or that parse to the same tree as the original,
    are dropped here: neither is a defect.
    """
    tree = ast.parse(source)
    original_dump = ast.dump(tree)
    source_lines = source.splitlines(keepends=True)
    skipped_constants = _docstring_ids(tree)

    seen: set[str] = set()
    mutants: list[Mutant] = []
    for node in ast.walk(tree):
        for app in _applications(node, skipped_constants):
            line = app.node.lineno
            if line not in lines or line > len(source_lines):
                continue
            raw = source_lines[line - 1]
            encoded = raw.encode("utf-8")
            start, end = app.node.col_offset, app.node.end_col_offset or 0
            old_text = encoded[start:end].decode("utf-8")
            new_text = app.rewrite(old_text)
            if new_text is None or new_text == old_text:
                continue
            new_line = (encoded[:start] + new_text.encode("utf-8") + encoded[end:]).decode("utf-8")
            mutated = "".join(source_lines[: line - 1]) + new_line + "".join(source_lines[line:])
            if mutated in seen:
                continue
            try:
                if ast.dump(ast.parse(mutated)) == original_dump:
                    continue
            except SyntaxError:
                continue
            seen.add(mutated)
            where = _enclosing_name(tree, line)
            location = f"{path}:{line}" + (f", in `{where}`" if where else "")
            mutants.append(
                Mutant(
                    edit=MutantEdit(
                        path=path,
                        start_line=line,
                        end_line=line,
                        original=raw.rstrip("\r\n"),
                        replacement=new_line.rstrip("\r\n"),
                        operator=app.operator,
                    ),
                    description=f"At {location}, {app.explain(old_text, new_text)}",
                    mutated_source=mutated,
                )
            )
    mutants.sort(key=lambda m: (m.edit.start_line, m.edit.operator, m.edit.replacement))
    return mutants


def implementation_hunk(source: str, line: int) -> str:
    """The innermost function or method holding `line`, else a window around it."""
    tree = ast.parse(source)
    source_lines = source.splitlines()
    span: tuple[int, int] | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            last = node.end_lineno or node.lineno
            if first <= line <= last and (span is None or first >= span[0]):
                span = (first, last)
    start, end = span if span else (line - _WINDOW, line + _WINDOW)
    if end - start + 1 > _MAX_HUNK_LINES:
        start, end = line - _WINDOW, line + _WINDOW
    start, end = max(start, 1), min(end, len(source_lines))
    return "\n".join(source_lines[start - 1 : end])


def _applications(node: ast.AST, skipped_constants: set[int]) -> Iterator[_Application]:
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and _one_line(node):
        gap = _gap(node, node.left, node.comparators[0])
        if gap:
            yield _Application(
                "compare_flip",
                node,
                _swap_in_gap(gap, _flip_comparison),
                lambda o, n: (
                    f"the comparison `{o}` is inverted to `{n}`, so it holds exactly where "
                    "the original did not."
                ),
            )
    if isinstance(node, ast.BoolOp) and len(node.values) == 2 and _one_line(node):
        gap = _gap(node, node.values[0], node.values[1])
        if gap:
            old, new = ("and", "or") if isinstance(node.op, ast.And) else ("or", "and")
            yield _Application(
                "boolop_swap",
                node,
                _swap_in_gap(gap, _word_swap(old, new)),
                lambda o, n, old=old, new=new: (
                    f"`{old}` is replaced by `{new}`, so `{o}` becomes `{n}`."
                ),
            )
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)) and _one_line(node):
        gap = _gap(node, node.left, node.right)
        if gap:
            old, new = ("+", "-") if isinstance(node.op, ast.Add) else ("-", "+")
            yield _Application(
                "arith_swap",
                node,
                _swap_in_gap(gap, _symbol_swap(old, new)),
                lambda o, n, old=old, new=new: (
                    f"`{old}` is replaced by `{new}`, so `{o}` becomes `{n}`."
                ),
            )
    if isinstance(node, ast.Constant) and _one_line(node) and id(node) not in skipped_constants:
        replacement = _changed_constant(node.value)
        if replacement is not None:
            yield _Application(
                "constant_change",
                node,
                lambda _old, r=replacement: r,
                lambda o, n: f"the constant `{o}` is changed to `{n}`.",
            )
    if isinstance(node, (ast.If, ast.While, ast.IfExp)) and _one_line(node.test):
        yield _Application(
            "negate_condition",
            node.test,
            lambda old: f"not ({old})",
            lambda o, n: (
                f"the condition `{o}` is negated to `{n}`, so the branch is taken exactly "
                "when it previously was not."
            ),
        )
    if (
        isinstance(node, ast.Return)
        and node.value is not None
        and not (isinstance(node.value, ast.Constant) and node.value.value is None)
        and _one_line(node.value)
    ):
        yield _Application(
            "return_none",
            node.value,
            lambda _old: "None",
            lambda o, n: f"the returned value `{o}` is replaced by `None`.",
        )
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and _one_line(node):
        operand = node.operand
        offset = operand.col_offset - node.col_offset
        yield _Application(
            "remove_not",
            node,
            lambda old, offset=offset: _bytes_from(old, offset),
            lambda o, n: f"the negation is removed, so `{o}` becomes `{n}`.",
        )


def _gap(node: ast.AST, left: ast.AST, right: ast.AST) -> tuple[int, int] | None:
    """Byte offsets, relative to `node`'s own text, of the span between two children."""
    if not (left.end_lineno == right.lineno == node.lineno):
        return None
    return (left.end_col_offset or 0) - node.col_offset, right.col_offset - node.col_offset


def _swap_in_gap(gap: tuple[int, int], swap: Callable[[str], str | None]) -> Rewrite:
    def rewrite(old: str) -> str | None:
        encoded = old.encode("utf-8")
        middle = swap(encoded[gap[0] : gap[1]].decode("utf-8"))
        if middle is None:
            return None
        return (encoded[: gap[0]] + middle.encode("utf-8") + encoded[gap[1] :]).decode("utf-8")

    return rewrite


def _flip_comparison(between: str) -> str | None:
    match = _COMPARE_TOKEN.search(between)
    if match is None:
        return None
    token = re.sub(r"\s+", " ", match.group(0))
    return between[: match.start()] + _COMPARE_FLIP[token] + between[match.end() :]


def _word_swap(old: str, new: str) -> Callable[[str], str | None]:
    def swap(between: str) -> str | None:
        replaced, count = re.subn(rf"\b{old}\b", new, between, count=1)
        return replaced if count else None

    return swap


def _symbol_swap(old: str, new: str) -> Callable[[str], str | None]:
    def swap(between: str) -> str | None:
        index = between.find(old)
        return None if index < 0 else between[:index] + new + between[index + 1 :]

    return swap


def _bytes_from(text: str, offset: int) -> str:
    return text.encode("utf-8")[offset:].decode("utf-8")


def _one_line(node: ast.AST) -> bool:
    return getattr(node, "lineno", None) is not None and node.lineno == node.end_lineno


def _changed_constant(value: object) -> str | None:
    if isinstance(value, bool):
        return "False" if value else "True"
    if isinstance(value, int):
        return str(value + 1)
    if isinstance(value, float):
        return repr(value + 1.0)
    if isinstance(value, str) and value:
        return "''"
    return None


def _docstring_ids(tree: ast.AST) -> set[int]:
    """Constants never mutated: docstrings, and the literal parts of f-strings."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
        if isinstance(node, ast.JoinedStr):
            ids.update(id(v) for v in node.values if isinstance(v, ast.Constant))
    return ids


def _enclosing_name(tree: ast.AST, line: int) -> str | None:
    best: tuple[int, str] | None = None
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.lineno <= line <= (node.end_lineno or node.lineno)
            and (best is None or node.lineno >= best[0])
        ):
            best = (node.lineno, node.name)
    return best[1] if best else None
