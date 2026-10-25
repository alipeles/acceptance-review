"""The code Jev is shown about one (defect, test) pair (#385).

DR-379's rule was measured with this context, built by
`docs/experiments/jev/m52/targeted_prompt.py`, and this is that builder applied
to the pipeline's own types:

- **the defect's code**: for each region the defect names, the innermost
  function holding it (with its class header when it is a method), from the
  file as delivered, with the region's lines marked; the top-level statement
  instead when a region is not in a function;
- **the test**: its file's import lines, its class header for a method, the
  test itself, and the fixtures and helpers it names, found in its own file or
  a `conftest.py` above it;
- **called code**: for every name the test or those helpers call, its
  definition in the project's non-test source, when the name is defined in at
  most `MAX_DEFS` places. A name defined more often is skipped as ambiguous.

**One difference from the experiment, and it is the owner's decision
(2026-10-24).** The experiment showed Jev a mutant: the edited line, with the
original and the replacement. A pair here has no edit — the defect is a
description, and the judge sees exactly the defects nothing turned into an edit
— so the marked lines are the region the defect names, and the description
stands where the edit stood. DR-379's figures were not measured on that, and
#385's benchmark item is the first check of it.

Bounded by `BUDGET` estimated tokens; a definition that does not fit is
dropped and the drop recorded, as the experiment did.
"""

from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from acceptance.evidence.discovery import DiscoveredTest
from acceptance.mutation.region import Region, regions_for
from acceptance.review_state import ChangeSet, Defect

__all__ = ["BUDGET", "MARK", "CodeIndex", "TargetedContext", "build_context"]

BUDGET = 12_000
MAX_DEFS = 2
MAX_DEF_LINES = 120
MARK = "  # <-- marked line"

# Directories whose modules are not the project's own source: tests, docs, and
# anything vendored or generated. A directory whose name starts with a dot is
# skipped as well, which is what keeps a `.venv` out of the index.
_SKIP_DIRS = frozenset(
    {
        "test",
        "tests",
        "docs",
        "doc",
        "build",
        "dist",
        "__pycache__",
        "venv",
        "node_modules",
        "site-packages",
    }
)


def _estimate(text: str) -> int:
    """Estimated Jev tokens. 2.8 characters per token, the experiment's measure
    on Jev's own counts: 4 under-counted enough to be refused as too long."""
    return int(len(text) / 2.8)


@dataclass
class TargetedContext:
    """What Jev is shown, and a record of every inclusion and drop."""

    code: str
    test: str
    called: str
    included: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _definitions(tree: ast.AST):
    """(name, node, enclosing class or None) for every function and class.

    A method is yielded once, with its class. `ast.walk` reaches it a second
    time on its own, and that copy, with no class, would otherwise win a tie on
    start line and drop the class header.
    """
    methods: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            yield node.name, node, None
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.add(id(child))
                    yield child.name, child, node
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and id(node) not in methods:
            yield node.name, node, None


def _start(node: ast.AST) -> int:
    return min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])


def _is_project_source(relative: PurePosixPath) -> bool:
    directories = relative.parts[:-1]
    if any(part in _SKIP_DIRS or part.startswith(".") for part in directories):
        return False
    return not relative.name.startswith("test") and relative.name != "conftest.py"


class CodeIndex:
    """Where each function and class name is defined in the project's source.

    Built once per judgement run rather than per pair: the walk reads every
    module, and a review asks about thousands of pairs over the same tree.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self._by_name: dict[str, list[tuple[str, int, int, int | None]]] = {}
        self._lines: dict[str, list[str]] = {}
        for path in sorted(root.rglob("*.py")):
            relative = PurePosixPath(path.relative_to(root).as_posix())
            if not _is_project_source(relative):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except (OSError, SyntaxError, ValueError):
                continue
            seen: set[tuple[str, int]] = set()
            for name, node, cls in _definitions(tree):
                start = _start(node)
                if (name, start) in seen:
                    continue
                seen.add((name, start))
                self._by_name.setdefault(name, []).append(
                    (str(relative), start, node.end_lineno or start, cls.lineno if cls else None)
                )

    def definitions(self, name: str) -> list[tuple[str, int, int, int | None]]:
        return self._by_name.get(name, [])

    def lines(self, relative: str) -> list[str]:
        if relative not in self._lines:
            path = self.root / relative
            try:
                self._lines[relative] = path.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()
            except OSError:
                self._lines[relative] = []
        return self._lines[relative]


def _span_text(lines: list[str], start: int, end: int, class_line: int | None) -> str:
    body = lines[start - 1 : end]
    if len(body) > MAX_DEF_LINES:
        body = body[:MAX_DEF_LINES] + ["    ... (truncated)"]
    head = [lines[class_line - 1], "    ..."] if class_line else []
    return "\n".join(head + body)


def _enclosing(tree: ast.Module, line: int) -> tuple[int, int, int | None] | None:
    """The innermost function holding `line`, else its top-level statement."""
    best: tuple[int, int, int | None] | None = None
    for _, node, cls in _definitions(tree):
        if isinstance(node, ast.ClassDef):
            continue
        start, end = _start(node), node.end_lineno or node.lineno
        if start <= line <= end and (best is None or start >= best[0]):
            best = (start, end, cls.lineno if cls else None)
    if best is not None:
        return best
    for node in tree.body:
        if node.lineno <= line <= (node.end_lineno or node.lineno):
            return (_start(node), node.end_lineno or node.lineno, None)
    return None


def _defect_code(
    regions: list[Region], index: CodeIndex, context: TargetedContext
) -> list[tuple[str, int, int]]:
    """Render each region's enclosing code with the region's lines marked.

    Returns the spans sent, so the called-code pass does not send them twice.
    """
    by_path: dict[str, list[Region]] = {}
    for region in regions:
        by_path.setdefault(region.path, []).append(region)

    blocks: list[str] = []
    sent: list[tuple[str, int, int]] = []
    for path in sorted(by_path):
        lines = index.lines(path)
        if not lines:
            context.skipped.append(f"defect code: {path} could not be read")
            continue
        try:
            tree = ast.parse("\n".join(lines))
        except (SyntaxError, ValueError):
            tree = None
        marked = {
            number
            for region in by_path[path]
            for number in range(region.start_line, region.end_line + 1)
        }
        spans: list[tuple[int, int, int | None]] = []
        for region in sorted(by_path[path], key=lambda r: r.start_line):
            found = _enclosing(tree, region.start_line) if tree is not None else None
            span = found or (region.start_line, region.end_line, None)
            # A region running past its function's end widens the span to it.
            span = (span[0], max(span[1], region.end_line), span[2])
            if not any(s[0] <= span[0] and span[1] <= s[1] for s in spans):
                spans.append(span)
        for start, end, class_line in spans:
            body = [
                line + MARK if number in marked else line
                for number, line in enumerate(lines[start - 1 : end], start=start)
            ]
            head = [lines[class_line - 1], "    ..."] if class_line else []
            blocks.append(f"# {path}\n" + "\n".join(head + body))
            sent.append((path, start, end))
            context.included.append(f"defect code: {path}:{start}-{end}")
    context.code = "\n\n".join(blocks)
    return sent


def _parse_test(source: str) -> ast.Module:
    """Parse a test that may be an indented method.

    Dedenting fails when the body holds a multi-line string at column 0, so
    fall back to wrapping the source in a class.
    """
    try:
        return ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return ast.parse("class _Wrapper:\n" + source)


def _called_names(source: str) -> list[str]:
    try:
        tree = _parse_test(source)
    except SyntaxError:
        return []
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if name and name not in names:
                names.append(name)
    return names


def _parameter_names(source: str) -> list[str]:
    try:
        tree = _parse_test(source)
    except SyntaxError:
        return []
    function = next(
        (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))),
        None,
    )
    if function is None:
        return []
    return [a.arg for a in function.args.args if a.arg not in ("self", "cls")]


def _test_text(test: DiscoveredTest, root: Path, context: TargetedContext) -> list[str]:
    """Render the test with its imports, class header and helpers.

    Returns the helpers' sources, whose calls the called-code pass follows.
    """
    test_path = root / test.file
    try:
        test_text = test_path.read_text(encoding="utf-8", errors="replace")
        test_tree = ast.parse(test_text)
    except (OSError, SyntaxError, ValueError):
        context.skipped.append(f"test file: {test.file} could not be read")
        context.test = test.source
        return []
    test_lines = test_text.splitlines()
    imports = [
        "\n".join(test_lines[n.lineno - 1 : n.end_lineno])
        for n in test_tree.body
        if isinstance(n, (ast.Import, ast.ImportFrom))
    ]

    local: dict[str, tuple[str, list[str], ast.AST]] = {}
    conftests = [root / parent / "conftest.py" for parent in PurePosixPath(test.file).parents]
    for path in [test_path, *[c for c in conftests if c.is_file()]]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            continue
        for node in tree.body:
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and not node.name.startswith("test"):
                local.setdefault(
                    node.name, (path.relative_to(root).as_posix(), text.splitlines(), node)
                )

    helpers: list[str] = []
    for name in _parameter_names(test.source) + _called_names(test.source):
        if name not in local:
            continue
        relative, lines, node = local.pop(name)
        start = _start(node)
        helpers.append(_span_text(lines, start, node.end_lineno or start, None))
        context.included.append(f"test helper: {relative}:{start} {name}")

    class_header = ""
    parts = test.test_id.split("::")[1:]
    if len(parts) == 2:
        cls = next(
            (n for n in test_tree.body if isinstance(n, ast.ClassDef) and n.name == parts[0]),
            None,
        )
        if cls is not None:
            class_header = test_lines[cls.lineno - 1] + "\n    ...\n"
    context.test = "\n".join(imports) + "\n\n" + "\n\n".join(helpers + [class_header + test.source])
    return helpers


def build_context(
    defect: Defect,
    test: DiscoveredTest,
    change_set: ChangeSet,
    index: CodeIndex,
) -> TargetedContext:
    """Everything Jev is shown about `defect` against `test`.

    Deterministic in its inputs: every walk is sorted or follows source order,
    so the same tree yields the same request and the same recording key.
    """
    context = TargetedContext(code="", test="", called="")
    sent = _defect_code(regions_for(defect, change_set), index, context)
    helpers = _test_text(test, index.root, context)

    used = _estimate(context.code) + _estimate(context.test)
    names = _called_names(test.source)
    for helper in helpers:
        names += [name for name in _called_names(helper) if name not in names]
    chunks: list[str] = []
    for name in names:
        definitions = index.definitions(name)
        if not definitions:
            continue
        if len(definitions) > MAX_DEFS:
            context.skipped.append(f"{name}: ambiguous ({len(definitions)} definitions)")
            continue
        for relative, start, end, class_line in definitions:
            # Already shown as the defect's code, either way round: a definition
            # inside a sent span repeats it, and one holding a sent span — the
            # class around the defect's method — is the experiment's skip.
            if any(
                p == relative and ((s <= start and end <= e) or (start <= s and e <= end))
                for p, s, e in sent
            ):
                continue
            text = f"# {relative}\n" + _span_text(index.lines(relative), start, end, class_line)
            if used + _estimate(text) > BUDGET:
                context.skipped.append(
                    f"{name}: over budget ({relative}:{start}, ~{_estimate(text)} tokens)"
                )
                continue
            used += _estimate(text)
            chunks.append(text)
            context.included.append(f"called: {relative}:{start} {name}")
    context.called = "\n\n".join(chunks)
    return context
