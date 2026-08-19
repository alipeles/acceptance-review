"""The committed task-file corpus is built from committed inputs only (#258).

The corpus feeds two parametrized suites, so what it contains decides both what
those suites assert and how many cases they have. These tests pin the two
properties that made the previous version depend on uncommitted work: the
repository-root scratch file is not in it, and an entry that is not really there
does not reach a case.
"""

from __future__ import annotations

from pathlib import Path

from tests.requirement.corpus import REPO_ROOT, committed_task_files


def test_the_corpus_is_not_empty():
    """A glob matching nothing turns every parametrized case into zero tests,
    which reports as a pass."""
    assert committed_task_files()


def test_no_corpus_path_lies_outside_dogfood_logs():
    for path in committed_task_files():
        relative = path.relative_to(REPO_ROOT)
        assert relative.parts[0] == "dogfood-logs", f"{relative} is not a committed dogfood input"
        assert relative.name == "current-task.md"


def test_a_path_outside_dogfood_logs_is_not_a_case(tmp_path: Path):
    """Asserted against a corpus built to contain the near misses.

    `test_no_corpus_path_lies_outside_dogfood_logs` walks the *real* corpus,
    where every path is already correct — it would pass unchanged against a
    discovery that admits outside paths, because none is there to admit. The
    three planted here are the shapes a widened glob would pick up: a sibling
    directory, the corpus directory itself, and the repository root.
    """
    logs = tmp_path / "dogfood-logs"
    first = logs / "996-gate1-run1" / "current-task.md"
    second = logs / "997-gate1-run1" / "current-task.md"
    for committed in (first, second):
        committed.parent.mkdir(parents=True)
        committed.write_text("# Task\na committed run\n")

    (tmp_path / "current-task.md").write_text("# Task\nthe task in flight\n")
    (logs / "current-task.md").write_text("# Task\nloose in the corpus directory\n")
    sibling = tmp_path / "notes" / "current-task.md"
    sibling.parent.mkdir(parents=True)
    sibling.write_text("# Task\na sibling directory\n")

    found = committed_task_files(tmp_path)

    # Compared as an ordered list rather than as a membership test, so that
    # admitting an outside path and duplicating a valid one are both visible —
    # two committed entries are present precisely so duplication can show.
    assert found == [first, second]
    for outside in (tmp_path / "current-task.md", logs / "current-task.md", sibling):
        assert outside.is_file()
        assert outside not in found


def test_a_tree_with_no_committed_runs_yields_no_cases(tmp_path: Path):
    """The control for every non-emptiness assertion here.

    `test_the_corpus_is_not_empty` cannot tell "the corpus was found" from "the
    builder returns something regardless": both look like a non-empty list. This
    is the other half — pointed at a tree with no committed runs, the builder
    returns nothing, and the paths it must not fall back to are all present.
    """
    (tmp_path / "current-task.md").write_text("# Task\nthe task in flight\n")
    (tmp_path / "dogfood-logs").mkdir()
    (tmp_path / "dogfood-logs" / "current-task.md").write_text("# Task\nloose\n")

    assert committed_task_files(tmp_path) == []


def test_each_committed_file_yields_exactly_one_case(tmp_path: Path):
    """One case per file, and no file twice.

    Cardinality alone does not say this: a list that drops one file and repeats
    another has the right length and covers neither property.
    """
    logs = tmp_path / "dogfood-logs"
    first = logs / "996-gate1-run1" / "current-task.md"
    second = logs / "997-gate1-run1" / "current-task.md"
    for path in (first, second):
        path.parent.mkdir(parents=True)
        path.write_text("# Task\na committed run\n")

    found = committed_task_files(tmp_path)

    assert found == [first, second]
    assert len(found) == len(set(found))

    real = committed_task_files()
    assert len(real) == len(set(real))
    assert len(real) == len(list(REPO_ROOT.glob("dogfood-logs/*/current-task.md")))


def test_the_parse_test_enumerates_the_corpus_and_nothing_else():
    """The wiring, not just the helper.

    `committed_task_files` can be correct while the parametrize that consumes it
    is not — the pre-#258 call site built its own list and put the scratch file
    at the head of it. This pins the case list of the parse test to the corpus
    itself.
    """
    from tests.requirement.test_task_file import test_parses_every_committed_task_file

    (parametrize,) = [
        mark
        for mark in test_parses_every_committed_task_file.pytestmark
        if mark.name == "parametrize"
    ]
    argnames, argvalues = parametrize.args

    assert argnames == "path"
    assert list(argvalues) == committed_task_files()
    assert len(set(argvalues)) == len(list(argvalues))


def test_the_repository_root_task_file_is_not_a_case(tmp_path: Path):
    """The whole point of #258: the scratch file in flight is not an input."""
    (tmp_path / "current-task.md").write_text("# Task\nthe task in flight\n")
    run = tmp_path / "dogfood-logs" / "999-gate1-run1"
    run.mkdir(parents=True)
    (run / "current-task.md").write_text("# Task\na committed run\n")

    assert committed_task_files(tmp_path) == [run / "current-task.md"]


def test_an_entry_whose_target_is_missing_is_omitted(tmp_path: Path):
    """An entry that is not really there does not become a parametrized case.

    Read this as a property test, not as evidence for the `is_file()` filter in
    `committed_task_files`. Deleting that filter leaves this test green —
    checked by injection — because `glob` resolves a literal final component
    through `exists()` and never yields the dangling entry at all. The property
    is real and worth pinning; the mechanism holding it up is `glob`, and this
    test cannot tell the two apart.
    """
    logs = tmp_path / "dogfood-logs"
    real = logs / "998-gate1-run1" / "current-task.md"
    real.parent.mkdir(parents=True)
    real.write_text("# Task\na committed run\n")

    dangling = logs / "999-gate1-run1" / "current-task.md"
    dangling.parent.mkdir(parents=True)
    dangling.symlink_to(tmp_path / "gone" / "current-task.md")

    assert dangling.is_symlink()
    assert committed_task_files(tmp_path) == [real]
