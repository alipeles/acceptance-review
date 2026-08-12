"""Per-test structural extraction (M5.1, §9.3).

For each mapped candidate test, extract the structural facts §9.3's evidence
analysis reasons over: what production code it exercises, what it asserts, its
fixtures/mocks, its inputs, and — the load-bearing one — its expected-value
**provenance**. This is Python AST, no LLM: the *discrimination judgment* (would
the test fail under a plausible defect?) is the semantic step, and lands in
M5.2 over what this extracts. Keeping M5.1 structural also makes it
deterministic and directly testable.

Expected-value provenance is the circular-evidence signal (§9.4). A test that
computes its expected value from the same production code it claims to verify
can never fail — a defect corrupts both sides of the equality equally. We detect
this structurally: the "production symbols under test" are the names a test
imports from a **changed source module** (`from orders import _apply_tax, ...`);
if BOTH operands of an equality assertion reference such a symbol — after
resolving local variable assignments — the expected value is production-derived,
i.e. circular. A side that is a literal/constant is independent evidence.

Limitation: only `from <changed_module> import name` bindings are treated as
production symbols today; a plain `import orders; orders.f()` isn't traced (the
archetypes and typical circular tests use from-imports). Refining that is a
future step, not a silent gap.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

from acceptance.evidence.discovery import DiscoveredTest
from acceptance.evidence.mapping import MappingResult
from acceptance.review_state import ChangeSet, TestEvidence

_MOCK_NAMES = {
    "Mock",
    "MagicMock",
    "AsyncMock",
    "NonCallableMock",
    "patch",
    "mock_open",
    "create_autospec",
}
_ASSERT_EQ_METHODS = {"assertEqual", "assertNotEqual", "assertAlmostEqual"}


def extract_test_evidence(
    repo: Path,
    discovered_tests: list[DiscoveredTest],
    change_set: ChangeSet,
    mapping: MappingResult,
) -> list[TestEvidence]:
    """Extract a TestEvidence record for each discovered test (§15)."""
    changed_modules = {
        Path(f.path).stem
        for f in change_set.files
        if f.category == "source" and f.status != "deleted" and f.path.endswith(".py")
    }
    obligations_by_test = {m.test_id: m.obligation_ids for m in mapping.mappings}

    production_by_file: dict[str, set[str]] = {}
    evidence: list[TestEvidence] = []
    for test in discovered_tests:
        if test.file not in production_by_file:
            production_by_file[test.file] = _production_import_names(
                repo / test.file, changed_modules
            )
        func = parse_test_function(test.source)
        if func is None:
            continue
        evidence.append(
            _extract_one(
                test,
                func,
                production_by_file[test.file],
                obligations_by_test.get(test.test_id, []),
            )
        )
    return evidence


def _production_import_names(file_path: Path, changed_modules: set[str]) -> set[str]:
    """Names a test file imports from a changed source module — the production
    symbols under test, whose appearance on both sides of an assertion is the
    circular-evidence signal."""
    try:
        module = ast.parse(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return set()
    names: set[str] = set()
    for node in ast.walk(module):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.split(".")[0] in changed_modules
        ):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def parse_test_function(source: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Parse a `DiscoveredTest.source` snippet back into its function AST node —
    shared with weak_patterns.py (M5.4), which needs the raw body too."""
    try:
        module = ast.parse(textwrap.dedent(source))  # dedent: class methods are indented
    except SyntaxError:
        return None
    node = module.body[0] if module.body else None
    return node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else None


def _extract_one(
    test: DiscoveredTest,
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    production_symbols: set[str],
    mapped_obligations: list[str],
) -> TestEvidence:
    assignments = _collect_assignments(func)
    comparisons = _equality_comparisons(func)

    return TestEvidence(
        identifier=test.test_id,
        location=test.file,
        inputs=_production_call_sources(func, production_symbols),
        fixtures=_fixture_params(func),
        assertions=[ast.unparse(node) for node in _assert_nodes(func)],
        expected_value_provenance=_expected_value_provenance(
            comparisons, assignments, production_symbols
        ),
        mocks=_mock_usages(func),
        mapped_obligations=mapped_obligations,
    )


def _collect_assignments(func: ast.AST) -> dict[str, ast.expr]:
    """Local `name -> value` bindings (last assignment wins), including simple
    tuple unpacking, so an operand named `expected` can be traced to what built it."""
    assignments: dict[str, ast.expr] = {}
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = node.value
                elif (
                    isinstance(target, ast.Tuple)
                    and isinstance(node.value, ast.Tuple)
                    and len(target.elts) == len(node.value.elts)
                ):
                    for elt, value in zip(target.elts, node.value.elts):
                        if isinstance(elt, ast.Name):
                            assignments[elt.id] = value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
            assignments[node.target.id] = node.value
    return assignments


def _names_in(expr: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(expr):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def _production_refs(
    expr: ast.expr, assignments: dict[str, ast.expr], production: set[str], _depth: int = 0
) -> set[str]:
    """Production symbols an expression references, resolving local variables
    through their assignments (bounded) so `expected` reaches `_apply_tax`."""
    names = _names_in(expr)
    refs = names & production
    if _depth < 3:
        for name in names:
            if name in assignments:
                refs |= _production_refs(assignments[name], assignments, production, _depth + 1)
    return refs


def _equality_comparisons(func: ast.AST) -> list[tuple[ast.expr, ast.expr]]:
    """(left, right) operand pairs of equality checks — `a == b` in asserts and
    `assertEqual(a, b)`-style calls."""
    pairs: list[tuple[ast.expr, ast.expr]] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Compare) and any(
            isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops
        ):
            left = node.left
            for op, right in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq)):
                    pairs.append((left, right))
                left = right
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _ASSERT_EQ_METHODS
            and len(node.args) >= 2
        ):
            pairs.append((node.args[0], node.args[1]))
    return pairs


def _expected_value_provenance(
    comparisons: list[tuple[ast.expr, ast.expr]],
    assignments: dict[str, ast.expr],
    production: set[str],
) -> str | None:
    independent_seen = False
    for left, right in comparisons:
        left_prod = _production_refs(left, assignments, production)
        right_prod = _production_refs(right, assignments, production)
        if left_prod and right_prod:
            symbols = ", ".join(sorted(left_prod | right_prod))
            return (
                f"Circular: both sides of the assertion derive from production code "
                f"under test ({symbols}); the expected value cannot independently "
                f"detect a defect, since a bug corrupts both sides equally."
            )
        # Exactly one side references production (the actual); the other is an
        # independent literal/constant — normal, non-circular evidence.
        if bool(left_prod) != bool(right_prod):
            independent_seen = True
    if independent_seen:
        return (
            "Independent: the expected value is a literal/constant, not derived "
            "from the code under test."
        )
    return None


def _production_call_sources(func: ast.AST, production: set[str]) -> list[str]:
    """Unparsed calls to production symbols — what code the test exercises, with
    what inputs."""
    sources: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name in production:
                sources.add(ast.unparse(node))
    return sorted(sources)


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _fixture_params(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    return [arg.arg for arg in func.args.args if arg.arg != "self"]


def _assert_nodes(func: ast.AST) -> list[ast.Assert]:
    return [node for node in ast.walk(func) if isinstance(node, ast.Assert)]


def _mock_usages(func: ast.AST) -> list[str]:
    used: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id in _MOCK_NAMES:
            used.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in _MOCK_NAMES:
            used.add(node.attr)
    return sorted(used)
