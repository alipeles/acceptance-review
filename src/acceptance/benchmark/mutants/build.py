"""Build the executed kill/survive label set from prepared BugsInPy bugs (#372).

Offline: everything it needs was fetched by `prepare.py`. Per bug it

1. lists the tests in the bug's test file and keeps the ones pytest admits;
2. selects up to `tests_per_bug` of them — the tests `run_test.sh` names first,
   then others from the same file in a seeded order;
3. runs them on the untouched code with `establish_baseline`, so a test that is
   already red, or that misbehaves in a copy, is set aside rather than labelled;
4. generates the fixed-operator mutants on the lines the fix changed and keeps
   up to `mutants_per_bug`, chosen in a seeded order;
5. runs the usable tests against each mutant, in a copy, in the sandbox.

One case is one (mutant, test) pair whose run completed. Every random choice is
seeded from the bug's key, and the output is canonical JSON with sorted lists,
so rebuilding from the same pins reproduces the file.
"""

from __future__ import annotations

import ast
import random
from collections.abc import Callable
from pathlib import Path

from acceptance.benchmark.mutants.bugsinpy import (
    BugInfo,
    PinnedBugs,
    fix_lines,
    read_bug,
    trigger_test_ids,
)
from acceptance.benchmark.mutants.labels import (
    MutantCase,
    MutantLabelSet,
    SetAsideMutant,
    SetAsideTestRecord,
    SkippedBug,
)
from acceptance.benchmark.mutants.operators import Mutant, generate_mutants, implementation_hunk
from acceptance.benchmark.mutants.prepare import LabelPaths
from acceptance.execution.outcome import SandboxRunResult, TestOutcomeKind
from acceptance.execution.sandbox import SandboxConfig, collect_tests, run_tests
from acceptance.mutation.baseline import Baseline, establish_baseline
from acceptance.mutation.workspace import copied_project
from acceptance.serialization import canonical_json

__all__ = ["build", "list_test_ids", "source_of_test", "write_labels"]

Runner = Callable[[list[str], Path, SandboxConfig], SandboxRunResult]


def build(
    pins: PinnedBugs,
    paths: LabelPaths,
    log: Callable[[str], None] = print,
    runner: Runner = run_tests,
    baseline: Callable[[list[str], Path, SandboxConfig], Baseline] = establish_baseline,
    collector: Callable[[list[str], Path, SandboxConfig], set[str]] = collect_tests,
) -> MutantLabelSet:
    """Build the whole set. The three callables exist so tests can stand in a
    fake sandbox; a real build uses the defaults."""
    result = MutantLabelSet(bugsinpy_commit=pins.bugsinpy_commit, bugs=list(pins.bugs))
    for key in pins.bugs:
        try:
            bug = read_bug(paths.dataset, key)
        except (OSError, KeyError) as error:
            result.skipped_bugs.append(SkippedBug(bug=key, reason=f"metadata unreadable: {error}"))
            continue
        reason = _missing(bug, paths)
        if reason:
            result.skipped_bugs.append(SkippedBug(bug=key, reason=reason))
            continue
        log(f"build {key}")
        # Never in place. The checkout lives inside this repository, and a
        # project with no pytest config of its own would otherwise have pytest
        # climb to OUR pyproject.toml: our rootdir, so every node id it reports
        # carries a `.acceptance/...` prefix and matches nothing, and our
        # addopts. That skipped 86 of 87 bugs on the first real build.
        with copied_project(paths.checkout(bug), prefix="acceptance-label-bug-") as root:
            _build_bug(bug, root, pins, paths, result, runner, baseline, collector)

    result.cases.sort(key=lambda c: c.case_id)
    result.set_aside_tests.sort(key=lambda t: (t.project, t.bug_id, t.test_id))
    result.set_aside_mutants.sort(
        key=lambda m: (m.project, m.bug_id, m.edit.path, m.edit.start_line, m.edit.replacement)
    )
    result.skipped_bugs.sort(key=lambda s: s.bug)
    return result


def write_labels(labels: MutantLabelSet, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(labels.to_dict()) + "\n", encoding="utf-8")


def _missing(bug: BugInfo, paths: LabelPaths) -> str | None:
    if not paths.checkout(bug).is_dir():
        return "project source not fetched (run prepare)"
    if not paths.message(bug).is_file():
        return "fix commit message not fetched (run prepare)"
    if not paths.interpreter(bug.project).exists():
        return f"no environment for {bug.project} (run prepare)"
    return None


def _build_bug(
    bug: BugInfo,
    root: Path,
    pins: PinnedBugs,
    paths: LabelPaths,
    result: MutantLabelSet,
    runner: Runner,
    baseline: Callable[[list[str], Path, SandboxConfig], Baseline],
    collector: Callable[[list[str], Path, SandboxConfig], set[str]],
) -> None:
    config = SandboxConfig(interpreter=str(paths.interpreter(bug.project).absolute()))

    test_path = root / bug.test_file
    if not test_path.is_file():
        result.skipped_bugs.append(SkippedBug(bug=bug.key, reason=f"no file {bug.test_file}"))
        return
    test_text = test_path.read_text(encoding="utf-8", errors="replace")
    listed = list_test_ids(test_text, bug.test_file)
    admitted = collector(listed, root, config) if listed else set()
    if not admitted:
        result.skipped_bugs.append(
            SkippedBug(bug=bug.key, reason=f"pytest admits no test in {bug.test_file}")
        )
        return

    selected = _select_tests(bug, sorted(admitted), pins.tests_per_bug)
    control = baseline(selected, root, config)
    for test in control.set_aside:
        result.set_aside_tests.append(
            SetAsideTestRecord(
                project=bug.project,
                bug_id=bug.bug_id,
                test_id=test.test_id,
                kind=test.kind.value,
                reason=test.reason,
            )
        )
    usable = sorted(control.usable_tests)
    if not usable:
        result.skipped_bugs.append(
            SkippedBug(bug=bug.key, reason="every selected test was set aside by the control run")
        )
        return

    mutants = _select_mutants(bug, root, pins.mutants_per_bug)
    if not mutants:
        result.skipped_bugs.append(
            SkippedBug(bug=bug.key, reason="no operator applies on the lines the fix changed")
        )
        return

    requirement = paths.message(bug).read_text(encoding="utf-8").strip()
    sources = {test_id: source_of_test(test_text, test_id) for test_id in usable}
    for index, mutant in enumerate(mutants):
        outcomes = _run_mutant(mutant, root, usable, config, runner)
        completed = [
            o
            for o in outcomes.outcomes
            if o.kind in (TestOutcomeKind.PASSED, TestOutcomeKind.FAILED)
        ]
        incomplete = [o for o in outcomes.outcomes if o not in completed]
        if incomplete:
            kinds = sorted({o.kind.value for o in incomplete})
            result.set_aside_mutants.append(
                SetAsideMutant(
                    project=bug.project,
                    bug_id=bug.bug_id,
                    edit=mutant.edit,
                    reason=(
                        f"{len(incomplete)} of {len(usable)} tests did not complete "
                        f"({', '.join(kinds)}); those pairs are not labelled"
                    ),
                )
            )
        hunk = implementation_hunk(
            (root / mutant.edit.path).read_text(encoding="utf-8"), mutant.edit.start_line
        )
        for outcome in completed:
            result.cases.append(
                MutantCase(
                    case_id=f"{bug.key}/m{index}/{outcome.test_id}",
                    source="bugsinpy-operator",
                    project=bug.project,
                    bug_id=bug.bug_id,
                    fixed_commit=bug.fixed_commit,
                    requirement_text=requirement,
                    test_id=outcome.test_id,
                    test_source=sources.get(outcome.test_id, ""),
                    implementation_hunk=hunk,
                    defect_description=mutant.description,
                    edit=mutant.edit,
                    killed=outcome.kind is TestOutcomeKind.FAILED,
                )
            )


def _run_mutant(
    mutant: Mutant, root: Path, tests: list[str], config: SandboxConfig, runner: Runner
) -> SandboxRunResult:
    with copied_project(root, prefix="acceptance-mutant-label-") as copy:
        (copy / mutant.edit.path).write_text(mutant.mutated_source, encoding="utf-8")
        return runner(tests, copy, config)


def _select_tests(bug: BugInfo, admitted: list[str], limit: int) -> list[str]:
    """The bug's own trigger tests first, then others from the file, seeded."""
    triggers = [t for t in dict.fromkeys(_bare(t) for t in trigger_test_ids(bug.run_test))]
    chosen = [t for t in triggers if t in admitted][:limit]
    rest = [t for t in admitted if t not in chosen]
    random.Random(f"{bug.key}/tests").shuffle(rest)
    return chosen + rest[: limit - len(chosen)]


def _select_mutants(bug: BugInfo, root: Path, limit: int) -> list[Mutant]:
    candidates: list[Mutant] = []
    for path, lines in sorted(fix_lines(bug.patch).items()):
        file = root / path
        if not file.is_file():
            continue
        try:
            candidates.extend(generate_mutants(file.read_text(encoding="utf-8"), path, lines))
        except (SyntaxError, UnicodeDecodeError, ValueError):
            continue
    if len(candidates) <= limit:
        return candidates
    picked = random.Random(f"{bug.key}/mutants").sample(range(len(candidates)), limit)
    return [candidates[i] for i in sorted(picked)]


def _bare(test_id: str) -> str:
    return test_id.split("[", 1)[0]


def list_test_ids(test_text: str, test_file: str) -> list[str]:
    """Test ids in a test file, read from its source the way pytest names them.

    Module-level `test*` functions, and `test*` methods of classes named `Test*`
    or deriving from something named `*TestCase`. `collect_tests` then keeps
    only the ones pytest really admits, so a miss here costs a test, never a
    wrong id.
    """
    try:
        tree = ast.parse(test_text)
    except SyntaxError:
        return []
    ids: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test"
        ):
            ids.append(f"{test_file}::{node.name}")
        elif isinstance(node, ast.ClassDef) and _is_test_class(node):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    item.name.startswith("test")
                ):
                    ids.append(f"{test_file}::{node.name}::{item.name}")
    return ids


def source_of_test(test_text: str, test_id: str) -> str:
    """The source of the function or method a test id names, decorators included."""
    names = test_id.split("::")[1:]
    tree = ast.parse(test_text)
    body: list[ast.stmt] = tree.body
    found: ast.AST | None = None
    for name in names:
        found = next(
            (
                n
                for n in body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and n.name == name
            ),
            None,
        )
        if found is None:
            return ""
        body = getattr(found, "body", [])
    lines = test_text.splitlines()
    first = min([found.lineno] + [d.lineno for d in found.decorator_list])
    return "\n".join(lines[first - 1 : found.end_lineno])


def _is_test_class(node: ast.ClassDef) -> bool:
    if node.name.startswith("Test"):
        return True
    for base in node.bases:
        name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
        if name.endswith("TestCase"):
            return True
    return False
