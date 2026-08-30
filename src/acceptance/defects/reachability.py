"""Keep a (defect, test) pair out of the judged set only when it cannot be wrong.

#314's rule is *include unless a static path is provably absent*, and DR-312's
resolved question 2 rules out building the machinery that would make most
absences provable: no name resolution, no transitive edges. Python makes that a
tar pit — dynamic dispatch, fixtures, pytest indirection — and an unvalidated
reachability component in front of the judge is worse than none.

**So this filter excludes almost nothing, and that is the accepted design, not a
shortfall.** The failure modes are asymmetric. A wrong exclusion silently
un-covers a defect and re-creates the recommendation that prescribes a test which
already exists (#250, #287) — the exact failure #312 exists to remove. A filter
that excludes too little only costs money, and the money is measured. Given that
trade, the rule below refuses to guess.

## What is NOT a proof, and why the obvious rule is rejected

`evidence/discovery.py` intersects a test's called names, referenced names and
imported module stems with the changed symbols and module stems. It is tempting
to read the absence of that intersection as "cannot reach". It is not:

    # tests/test_invoice.py
    from helpers import make_invoice          # imports helpers, not billing
    def test_total():
        assert make_invoice().total == 100    # references make_invoice, not charge

`make_invoice` calls `billing.charge`. The test references no changed name and
imports no changed module, and it would still fail on a defect in `charge`.
Excluding that pair loses a real kill silently. One hop cannot see the second
edge, so one hop cannot prove absence.

## What IS a proof

A test can reach repo code three ways: by referencing a name directly, by
routing through a module it imports, or by receiving a pytest fixture. Close all
three and the absence is genuine rather than assumed:

1. the defect names at least one implicated file — with none, nothing is known;
2. the test is not defined in one of those files;
3. the test's module imports no first-party module at all, so there is no helper
   for a call to route through;
4. the test function takes no arguments, so no fixture can hand it anything;
5. the test's module uses no dynamic import or evaluation machinery;
6. the test references none of the names defined in the defect's files.

Together those leave no path. Drop any one and the proof fails, so any one
failing means the pair is judged.

Condition 3 is what makes this rare in practice: almost every real test imports
something first-party. That is expected. The recorded-exclusion behaviour is
proved on a constructed fixture rather than on incidental real input, because a
rule that fires by luck is not a tested rule.

Every exclusion is recorded with both ids and a reason — never dropped. DR-164's
silent id filter is the precedent for why an invisible exclusion is the dangerous
kind.
"""

from __future__ import annotations

import ast
from pathlib import Path

from acceptance.change.context import changed_definitions
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.review_state import ChangeSet, Defect, UnjudgedCause, UnjudgedPair

__all__ = ["Pair", "form_pairs", "prefilter"]

# Names whose presence in a test module means we cannot reason about what it
# reaches. Any one of them can produce an import or a call this filter cannot
# see, so a module using one is never the basis of an exclusion.
_DYNAMIC = frozenset(
    {"importlib", "__import__", "exec", "eval", "compile", "globals", "locals", "getattr"}
)

# Directories whose modules are not this repo's own code. Vendored and generated
# trees would otherwise flood the first-party set with names like `json`, and a
# test importing the real `json` would then look like it took a second hop.
_NOT_REPO_CODE = frozenset(
    {"__pycache__", "venv", "node_modules", "build", "dist", "site-packages"}
)


class Pair:
    """One defect and one test, the unit the stage judges and carries."""

    __slots__ = ("defect", "test")

    def __init__(self, defect: Defect, test: DiscoveredTest) -> None:
        self.defect = defect
        self.test = test

    @property
    def key(self) -> tuple[str, str]:
        return (self.defect.id, self.test.test_id)


def form_pairs(defects: list[Defect], tests: list[DiscoveredTest]) -> list[Pair]:
    """Every defect against every test, in a fixed order.

    Sorted rather than left in discovery order because the order reaches the
    request, and a request whose content depends on how the filesystem was
    walked is not byte-reproducible.
    """
    return [
        Pair(defect, test)
        for defect in sorted(defects, key=lambda d: d.id)
        for test in sorted(tests, key=lambda t: t.test_id)
    ]


def _implicated_files(defect: Defect) -> set[str]:
    """The files the defect's `path#hunk` code refs name."""
    return {ref.split("#", 1)[0] for ref in defect.code_refs if ref}


def _module_of(repo: Path, path: str, cache: dict[str, ast.Module | None]) -> ast.Module | None:
    if path not in cache:
        try:
            source = (repo / path).read_text(encoding="utf-8")
            cache[path] = ast.parse(source)
        except (OSError, SyntaxError, UnicodeDecodeError):
            # Unreadable or unparseable is the conservative direction: no module
            # means no proof, and no proof means the pair is judged.
            cache[path] = None
    return cache[path]


def _first_party_stems(repo: Path) -> set[str]:
    """Top-level module and package names that live in this repo.

    Anything importable from the repo itself is a possible second hop. Computed
    from the tree rather than guessed from a package name, so a flat repo with
    loose modules at the root is covered as well as a `src/` layout.
    """
    stems: set[str] = set()
    for path in repo.rglob("*.py"):
        parts = path.relative_to(repo).parts
        if any(part.startswith(".") or part in _NOT_REPO_CODE for part in parts):
            continue
        stems.add(path.stem)
        for part in parts[:-1]:
            stems.add(part)
    return stems


def _imports_first_party(module: ast.Module, first_party: set[str]) -> bool:
    """Whether the module imports anything that could be this repo's own code.

    A relative import counts unconditionally: it names a sibling this filter
    cannot resolve without following the edge, which is the transitive step that
    is out of scope. Returning True there keeps the pair judged, which is the
    direction a failed proof always takes.
    """
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] in first_party for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                return True
            if node.module and node.module.split(".")[0] in first_party:
                return True
    return False


def _uses_dynamic(module: ast.Module) -> bool:
    for node in ast.walk(module):
        if isinstance(node, ast.Name) and node.id in _DYNAMIC:
            return True
        if isinstance(node, ast.Attribute) and node.attr in _DYNAMIC:
            return True
    return False


def _takes_arguments(test_id: str, module: ast.Module) -> bool:
    """Whether the named test function declares any parameter.

    A parameter is a pytest fixture request, and a fixture can hand the test
    anything at all — including a call into the defect's code. `self` on a
    method does not count; it carries no fixture.

    Returns True when the function cannot be found, because an unlocatable test
    is an unproven one.
    """
    wanted = test_id.split("::")[-1]
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == wanted:
            args = node.args
            names = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
            names = [name for name in names if name not in ("self", "cls")]
            return bool(names or args.vararg or args.kwarg)
    return True


def _defined_names(repo: Path, change_set: ChangeSet, files: set[str]) -> set[str]:
    """Names defined in the given files, by their changed definitions.

    A superset of the names in the defect's own hunks, deliberately: taking the
    whole file makes condition 6 harder to satisfy, so the exclusion is harder to
    earn, which is the safe direction.
    """
    return {
        definition.qualname.rsplit(".", 1)[-1]
        for definition in changed_definitions(repo, change_set)
        if definition.file in files
    }


def _referenced(module: ast.Module, test_id: str) -> set[str]:
    """Every name the test function calls or refers to."""
    wanted = test_id.split("::")[-1]
    names: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == wanted:
            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    names.add(child.id)
                elif isinstance(child, ast.Attribute):
                    names.add(child.attr)
    return names


class _Prover:
    """Holds what proving costs: the repo's own module names, parsed test
    modules, and the defined-name sets. All are shared across pairs, and all are
    computed only when a pair gets far enough to need them."""

    def __init__(self, repo: Path, change_set: ChangeSet) -> None:
        self.repo = repo
        self.change_set = change_set
        self._first_party: set[str] | None = None
        self._modules: dict[str, ast.Module | None] = {}
        self._defined: dict[frozenset[str], set[str]] = {}

    def first_party(self) -> set[str]:
        if self._first_party is None:
            self._first_party = _first_party_stems(self.repo)
        return self._first_party

    def module(self, path: str) -> ast.Module | None:
        return _module_of(self.repo, path, self._modules)

    def defined(self, files: set[str]) -> set[str]:
        key = frozenset(files)
        if key not in self._defined:
            self._defined[key] = _defined_names(self.repo, self.change_set, files)
        return self._defined[key]


def _exclusion_reason(pair: Pair, prover: _Prover) -> str | None:
    """Why this pair provably needs no judgement, or None to judge it.

    Every early return is a failed proof, and a failed proof means the pair is
    judged. That direction is the whole design: see the module docstring on why a
    wrong exclusion costs more than a wasted call.
    """
    files = _implicated_files(pair.defect)
    if not files:
        return None  # nothing known about where the defect lives
    if pair.test.file in files:
        return None  # the test sits in one of the defect's own files

    module = prover.module(pair.test.file)
    if module is None:
        return None  # unreadable or unparseable, so nothing is proven
    if _uses_dynamic(module):
        return None  # the module can reach things this filter cannot see
    if _takes_arguments(pair.test.test_id, module):
        return None  # a fixture can hand the test anything
    if _imports_first_party(module, prover.first_party()):
        return None  # a first-party import is a second hop
    if _referenced(module, pair.test.test_id) & prover.defined(files):
        return None  # the test names something the defect's files define

    return (
        "the test's module imports no first-party module, the test takes no fixture, and it "
        f"references no name defined in {', '.join(sorted(files))} — no path to the defect exists"
    )


def prefilter(
    pairs: list[Pair], repo: Path, change_set: ChangeSet
) -> tuple[list[Pair], list[UnjudgedPair]]:
    """Split `pairs` into the ones to judge and the ones provably not worth it.

    The second list is expected to be empty on most real input. An empty
    exclusion list means the filter ran and proved nothing absent — which is a
    different claim from "no filter ran", and the caller records it as such.
    """
    prover = _Prover(repo, change_set)
    judged: list[Pair] = []
    excluded: list[UnjudgedPair] = []

    for pair in pairs:
        reason = _exclusion_reason(pair, prover)
        if reason is None:
            judged.append(pair)
        else:
            excluded.append(
                UnjudgedPair(
                    defect_id=pair.defect.id,
                    test_id=pair.test.test_id,
                    cause=UnjudgedCause.PREFILTERED,
                    reason=reason,
                )
            )

    return judged, excluded
