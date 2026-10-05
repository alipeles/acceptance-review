"""#372's executed kill/survive labels: loader, operators, patch reading, build wiring.

The real labels are built from BugsInPy and never committed (DR-168), so
everything here runs on small synthetic inputs: a made-up label file, made-up
source, and a fake sandbox standing in for the test runs.
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from acceptance.benchmark.mutants.bugsinpy import (
    PinnedBugs,
    fix_lines,
    load_pinned_bugs,
    trigger_test_ids,
)
from acceptance.benchmark.mutants.build import build, list_test_ids, source_of_test, write_labels
from acceptance.benchmark.mutants.labels import (
    MutantEdit,
    MutantLabelSet,
    SurvivorCheck,
    SurvivorSample,
    load_mutant_labels,
)
from acceptance.benchmark.mutants.operators import generate_mutants, implementation_hunk
from acceptance.benchmark.mutants.prepare import LabelPaths, commit_message
from acceptance.benchmark.mutants.survivors import draw_survivor_sample, summarise
from acceptance.execution.outcome import SandboxRunResult, TestOutcome, TestOutcomeKind
from acceptance.execution.sandbox import collect_tests, run_tests
from acceptance.mutation.baseline import Baseline, SetAsideTest, establish_baseline

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mutant-labels" / "labels.json"


# --- the loader -------------------------------------------------------------


def test_loader_reads_the_synthetic_fixture_into_typed_cases():
    labels = load_mutant_labels(FIXTURE)

    assert labels.bugsinpy_commit == "0" * 40
    assert [c.killed for c in labels.cases] == [True, False]
    case = labels.cases[0]
    assert case.source == "bugsinpy-operator"
    assert case.edit.operator == "compare_flip"
    assert case.edit.replacement == "    return x <= 0"
    assert case.requirement_text.startswith("Fix sign check")
    assert case.test_source.startswith("def test_positive")


def test_loader_rejects_a_case_with_a_field_it_does_not_know(tmp_path):
    data = json.loads(FIXTURE.read_text())
    data["cases"][0]["confidence"] = 0.9
    path = tmp_path / "labels.json"
    path.write_text(json.dumps(data))

    with pytest.raises(ValidationError):
        load_mutant_labels(path)


def test_loader_rejects_two_cases_with_one_id(tmp_path):
    data = json.loads(FIXTURE.read_text())
    data["cases"][1]["case_id"] = data["cases"][0]["case_id"]
    path = tmp_path / "labels.json"
    path.write_text(json.dumps(data))

    with pytest.raises(ValidationError, match="appears twice"):
        load_mutant_labels(path)


def test_an_edit_that_changes_nothing_is_refused():
    with pytest.raises(ValidationError, match="injects nothing"):
        MutantEdit(
            path="m.py", start_line=1, end_line=1, original="x", replacement="x", operator="o"
        )


# --- the operators ----------------------------------------------------------

SOURCE = '''def f(x, items):
    """A docstring that must never be mutated."""
    if x > 0 and items:
        return x + 1
    return not items


def g():
    return 5
'''


def test_every_operator_edits_only_the_requested_lines_and_still_parses():
    mutants = generate_mutants(SOURCE, "m.py", {3, 4, 5})

    assert {m.edit.operator for m in mutants} == {
        "boolop_swap",
        "compare_flip",
        "constant_change",
        "negate_condition",
        "arith_swap",
        "return_none",
        "remove_not",
    }
    for mutant in mutants:
        assert mutant.edit.start_line in {3, 4, 5}
        ast.parse(mutant.mutated_source)
        original = SOURCE.splitlines()
        mutated = mutant.mutated_source.splitlines()
        changed = [i + 1 for i, (a, b) in enumerate(zip(original, mutated)) if a != b]
        assert changed == [mutant.edit.start_line]
        assert mutated[mutant.edit.start_line - 1] == mutant.edit.replacement


def test_the_description_quotes_the_exact_edit():
    flip = next(
        m for m in generate_mutants(SOURCE, "m.py", {3}) if m.edit.operator == "compare_flip"
    )

    assert flip.edit.replacement == "    if x <= 0 and items:"
    assert "`x > 0` is inverted to `x <= 0`" in flip.description
    assert flip.description.startswith("At m.py:3, in `f`,")


def test_docstrings_are_never_mutated():
    assert generate_mutants(SOURCE, "m.py", {2}) == []


def test_generation_is_deterministic():
    first = generate_mutants(SOURCE, "m.py", {3, 4, 5, 9})
    second = generate_mutants(SOURCE, "m.py", {3, 4, 5, 9})

    assert [m.edit for m in first] == [m.edit for m in second]


def test_a_utf8_line_is_spliced_at_the_right_bytes():
    source = 'def f(s):\n    return s == "é" or s == "ü"\n'
    flips = [m for m in generate_mutants(source, "m.py", {2}) if m.edit.operator == "compare_flip"]

    assert {m.edit.replacement for m in flips} == {
        '    return s != "é" or s == "ü"',
        '    return s == "é" or s != "ü"',
    }


def test_the_hunk_is_the_enclosing_function():
    assert implementation_hunk(SOURCE, 4).splitlines()[0] == "def f(x, items):"
    assert implementation_hunk(SOURCE, 9) == "def g():\n    return 5"


# --- reading BugsInPy -------------------------------------------------------

PATCH = """diff --git a/pkg/core.py b/pkg/core.py
index 1..2 100644
--- a/pkg/core.py
+++ b/pkg/core.py
@@ -10,7 +10,7 @@ def f():
     a = 1
     b = 2
-    return a > b
+    return a < b
     c = 3
@@ -30,3 +30,2 @@ def g():
     keep = 1
-    drop = 2
     tail = 3
diff --git a/tests/test_core.py b/tests/test_core.py
--- a/tests/test_core.py
+++ b/tests/test_core.py
@@ -1,1 +1,2 @@
 x = 1
+y = 2
"""


def test_fix_lines_are_the_new_side_lines_of_source_files_only():
    assert fix_lines(PATCH) == {"pkg/core.py": {12, 30, 31}}


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("pytest -q -s tests/test_a.py::test_x", ["tests/test_a.py::test_x"]),
        ("python3 -m pytest pkg/tests/t.py::test_y", ["pkg/tests/t.py::test_y"]),
        (
            "python -m unittest -q test.test_utils.TestUtil.test_match_str",
            ["test/test_utils.py::TestUtil::test_match_str"],
        ),
    ],
)
def test_trigger_tests_are_read_from_every_runner_form(command, expected):
    assert trigger_test_ids(command) == expected


def test_the_committed_pin_names_bugs_and_a_dataset_commit():
    pins = load_pinned_bugs()

    assert len(pins.bugsinpy_commit) == 40
    assert len(pins.bugs) == len(set(pins.bugs)) > 0
    assert {bug.split("/")[0] for bug in pins.bugs} <= set(pins.projects)


def test_a_commit_message_is_read_from_a_format_patch_email():
    patch = (
        "From abc Mon Sep 17 00:00:00 2001\n"
        "From: A <a@example.com>\n"
        "Subject: [PATCH] Fix sign check\n"
        " for zero\n\n"
        "Zero is not positive.\n"
        "---\n"
        " pkg/core.py | 2 +-\n"
    )

    assert commit_message(patch) == "Fix sign check for zero\n\nZero is not positive.\n"


# --- test listing -----------------------------------------------------------

TESTS = """import unittest


def test_one():
    assert True


class TestThing:
    def test_two(self):
        pass

    def helper(self):
        pass


class Legacy(unittest.TestCase):
    @staticmethod
    def test_three():
        pass
"""


def test_test_ids_are_listed_the_way_pytest_names_them():
    assert list_test_ids(TESTS, "t.py") == [
        "t.py::test_one",
        "t.py::TestThing::test_two",
        "t.py::Legacy::test_three",
    ]


def test_a_test_s_source_includes_its_decorators():
    assert source_of_test(TESTS, "t.py::Legacy::test_three") == (
        "    @staticmethod\n    def test_three():\n        pass"
    )


# --- the build, wired through a fake sandbox --------------------------------


def _project(tmp_path: Path) -> tuple[PinnedBugs, LabelPaths]:
    """A one-bug BugsInPy layout, already 'prepared'."""
    paths = LabelPaths(tmp_path / "labels")
    bug_dir = paths.dataset / "projects" / "demo" / "bugs" / "1"
    bug_dir.mkdir(parents=True)
    (paths.dataset / "projects" / "demo" / "project.info").write_text(
        'github_url="https://github.com/example/demo"\n'
    )
    (bug_dir / "bug.info").write_text(
        'buggy_commit_id="aaa"\nfixed_commit_id="bbb"\ntest_file="tests/test_core.py"\n'
    )
    (bug_dir / "run_test.sh").write_text("pytest tests/test_core.py::test_positive\n")
    (bug_dir / "bug_patch.txt").write_text(
        "--- a/demo/core.py\n+++ b/demo/core.py\n@@ -1,2 +1,2 @@\n"
        " def positive(x):\n-    return x >= 0\n+    return x > 0\n"
    )
    checkout = paths.projects / "demo-1"
    (checkout / "demo").mkdir(parents=True)
    (checkout / "tests").mkdir()
    (checkout / "demo" / "core.py").write_text("def positive(x):\n    return x > 0\n")
    (checkout / "tests" / "test_core.py").write_text(
        "def test_positive():\n    assert positive(1)\n\n\n"
        "def test_large():\n    assert positive(10**9)\n\n\n"
        "def test_unrelated():\n    assert True\n\n\n"
        "def test_red():\n    assert positive(-1)\n"
    )
    paths.message(_bug("demo", 1)).parent.mkdir(parents=True)
    paths.message(_bug("demo", 1)).write_text("Treat zero as not positive\n")
    paths.interpreter("demo").parent.mkdir(parents=True)
    paths.interpreter("demo").write_text("")
    pins = PinnedBugs(
        bugsinpy_commit="0" * 40,
        python="3.9",
        exclude_newer="2024-01-01T00:00:00Z",
        tests_per_bug=3,
        mutants_per_bug=10,
        projects={"demo": ["pytest"]},
        bugs=["demo/1"],
    )
    return pins, paths


def _bug(project, number):
    """Just the two fields `LabelPaths` reads from a bug."""
    return SimpleNamespace(project=project, bug_id=number)


class FakeSandbox:
    """Kills a mutant exactly when `test_positive` runs against changed source."""

    def __init__(self, original: str, never_completes: frozenset[str] = frozenset()):
        self.original = original
        self.never_completes = never_completes
        self.runs: list[tuple[list[str], Path]] = []

    def run(self, tests, root, config):
        self.runs.append((list(tests), root))
        mutated = (root / "demo" / "core.py").read_text() != self.original
        return SandboxRunResult(outcomes=[self._outcome(t, mutated) for t in tests])

    def _outcome(self, test_id, mutated):
        name = test_id.rsplit("::", 1)[-1]
        if mutated and name in self.never_completes:
            return TestOutcome(
                test_id=test_id, kind=TestOutcomeKind.TIMED_OUT, reason="ran past its budget"
            )
        failed = mutated and name == "test_positive"
        return TestOutcome(
            test_id=test_id, kind=TestOutcomeKind.FAILED if failed else TestOutcomeKind.PASSED
        )

    def baseline(self, tests, root, config):
        self.runs.append((list(tests), root))
        red = [t for t in tests if t.endswith("test_red")]
        return Baseline(
            usable_tests=[t for t in tests if t not in red],
            set_aside=[
                SetAsideTest(
                    test_id=t,
                    kind=TestOutcomeKind.FAILED,
                    reason="red",
                    error_type="AttributeError",
                    detail="'Function' object has no attribute 'get_marker'",
                )
                for t in red
            ],
        )

    def collect(self, tests, root, config):
        self.runs.append((list(tests), root))
        return set(tests)


PACKAGES = ["pytest==7.4.4"]


def _build(tmp_path, never_completes=frozenset(), packages=PACKAGES, patch=None):
    pins, paths = _project(tmp_path)
    if patch is not None:
        (paths.dataset / "projects" / "demo" / "bugs" / "1" / "bug_patch.txt").write_text(patch)
    sandbox = FakeSandbox("def positive(x):\n    return x > 0\n", frozenset(never_completes))
    labels = build(
        pins,
        paths,
        log=lambda _line: None,
        runner=sandbox.run,
        baseline=sandbox.baseline,
        collector=sandbox.collect,
        freezer=lambda _interpreter: list(packages),
    )
    return labels, sandbox, paths


def test_the_build_labels_every_usable_test_against_every_mutant(tmp_path):
    labels, _sandbox, _paths = _build(tmp_path)

    # The fix changed line 2, `return x > 0`: three operators apply there.
    assert {c.edit.replacement for c in labels.cases} == {
        "    return x <= 0",
        "    return x > 1",
        "    return None",
    }
    assert len(labels.cases) == 3 * 2
    # The trigger test, plus the one usable extra that calls `positive`.
    # `test_unrelated` never names the edited function, so it is never chosen.
    assert {c.test_id for c in labels.cases} == {
        "tests/test_core.py::test_positive",
        "tests/test_core.py::test_large",
    }
    for case in labels.cases:
        assert case.killed is case.test_id.endswith("test_positive")
        assert case.requirement_text == "Treat zero as not positive"
        assert case.implementation_hunk == "def positive(x):\n    return x > 0"


def test_nothing_runs_inside_the_prepared_checkout(tmp_path):
    """The checkout lives inside this repository, where pytest would climb to
    our own pyproject.toml and report every test under a prefixed id. Every
    collection, control run and mutant run must happen in a copy elsewhere."""
    labels, sandbox, paths = _build(tmp_path)

    assert labels.cases
    roots = [root.resolve() for _tests, root in sandbox.runs]
    assert len(roots) == 1 + 1 + 3  # collect, control run, three mutants
    for root in roots:
        assert root.name == "demo-1"
        assert not root.is_relative_to(paths.projects.resolve())


def test_a_red_test_is_set_aside_and_never_labelled(tmp_path):
    labels, _sandbox, _paths = _build(tmp_path)

    assert [t.test_id for t in labels.set_aside_tests] == ["tests/test_core.py::test_red"]
    # What actually went wrong survives into the label file, not just the
    # sentence every red test shares.
    assert labels.set_aside_tests[0].error_type == "AttributeError"
    assert "get_marker" in labels.set_aside_tests[0].detail
    assert not any(c.test_id.endswith("test_red") for c in labels.cases)


def test_a_bug_that_was_not_prepared_is_skipped_with_a_reason(tmp_path):
    pins, paths = _project(tmp_path)
    paths.message(_bug("demo", 1)).unlink()

    labels = build(pins, paths, log=lambda _line: None, freezer=lambda _i: PACKAGES)

    assert labels.cases == []
    assert labels.skipped_bugs[0].reason.startswith("fix commit message not fetched")


def test_killed_is_true_exactly_when_the_test_failed_with_the_edit_in_place(tmp_path):
    labels, _sandbox, _paths = _build(tmp_path)

    by_test = {}
    for case in labels.cases:
        by_test.setdefault(case.test_id.rsplit("::", 1)[-1], set()).add(case.killed)
    # The fake fails `test_positive` under every edit and passes `test_large`.
    assert by_test == {"test_positive": {True}, "test_large": {False}}


def test_a_run_that_never_completes_is_never_turned_into_a_label(tmp_path):
    labels, _sandbox, _paths = _build(tmp_path, never_completes={"test_large"})

    assert {c.test_id for c in labels.cases} == {"tests/test_core.py::test_positive"}
    # Each edit says how many of its pairs went unlabelled, and why.
    assert len(labels.set_aside_mutants) == 3
    for mutant in labels.set_aside_mutants:
        assert mutant.reason.startswith("1 of 2 tests did not complete (timed_out)")


def test_a_fix_to_a_test_file_or_a_non_python_file_is_never_mutated(tmp_path):
    patch = (
        "--- a/demo/core.py\n+++ b/demo/core.py\n@@ -1,2 +1,2 @@\n"
        " def positive(x):\n-    return x >= 0\n+    return x > 0\n"
        "--- a/tests/test_core.py\n+++ b/tests/test_core.py\n@@ -1,2 +1,2 @@\n"
        " def test_positive():\n-    assert positive(2)\n+    assert positive(1)\n"
        "--- a/README.md\n+++ b/README.md\n@@ -1,1 +1,1 @@\n-old\n+new\n"
    )

    labels, _sandbox, _paths = _build(tmp_path, patch=patch)

    assert labels.cases
    assert {c.edit.path for c in labels.cases} == {"demo/core.py"}


def test_a_real_build_runs_every_test_through_the_existing_sandbox():
    """Every other build test stands in a fake; this pins that the defaults a
    real build uses are the sandbox's own runner, collector and control run."""
    defaults = {
        name: parameter.default for name, parameter in inspect.signature(build).parameters.items()
    }

    assert defaults["runner"] is run_tests
    assert defaults["collector"] is collect_tests
    assert defaults["baseline"] is establish_baseline


def test_each_environment_s_packages_are_recorded_and_change_the_file(tmp_path):
    first, _s, _p = _build(tmp_path / "a", packages=["pytest==7.4.4"])
    second, _s2, _p2 = _build(tmp_path / "b", packages=["pytest==8.0.0"])

    assert first.environments == {"demo": ["pytest==7.4.4"]}
    write_labels(first, tmp_path / "one.json")
    write_labels(second, tmp_path / "two.json")
    assert (tmp_path / "one.json").read_bytes() != (tmp_path / "two.json").read_bytes()


def test_rebuilding_from_the_same_pins_writes_the_same_bytes(tmp_path):
    first, _s, _p = _build(tmp_path / "a")
    second, _s2, _p2 = _build(tmp_path / "b")
    write_labels(first, tmp_path / "one.json")
    write_labels(second, tmp_path / "two.json")

    assert (tmp_path / "one.json").read_bytes() == (tmp_path / "two.json").read_bytes()
    assert load_mutant_labels(tmp_path / "one.json") == first


# --- survivors and the report ------------------------------------------------


def test_the_survivor_sample_takes_one_case_per_edit_and_is_seeded(tmp_path):
    labels, _sandbox, _paths = _build(tmp_path)
    survivors_per_edit = {
        (c.edit.start_line, c.edit.replacement) for c in labels.cases if not c.killed
    }

    sample = draw_survivor_sample(labels, size=100, seed=1)

    assert sample.population == len(survivors_per_edit)
    assert len(sample.checks) == len(survivors_per_edit)
    assert draw_survivor_sample(labels, size=2, seed=1) == draw_survivor_sample(
        labels, size=2, seed=1
    )


def test_the_report_holds_counts_and_the_spot_check_share_only(tmp_path):
    labels, _sandbox, _paths = _build(tmp_path)
    sample = SurvivorSample(
        seed=1,
        population=4,
        checks=[
            SurvivorCheck(case_id="a", changes_behaviour=True),
            SurvivorCheck(case_id="b", changes_behaviour=False),
            SurvivorCheck(case_id="c"),
        ],
    )

    summary = summarise(labels, sample)

    assert summary["cases"] == summary["killed"] + summary["survived"]
    assert summary["survivor_check"] == {
        "population": 4,
        "sample_size": 3,
        "checked": 2,
        "no_behaviour_change": 1,
        "no_behaviour_change_share": 0.5,
    }
    # Nothing in the report is text from the project under test.
    flat = json.dumps(summary)
    for text in ("x > 0", "Treat zero", "test_positive", "demo/core.py"):
        assert text not in flat


def test_an_empty_label_set_still_summarises():
    summary = summarise(MutantLabelSet(bugsinpy_commit="0" * 40, bugs=[]))

    assert summary["cases"] == 0 and summary["killed_share"] is None
