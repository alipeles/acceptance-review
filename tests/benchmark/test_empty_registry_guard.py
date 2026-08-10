"""#228: a benchmark case whose task file yields no requirements must fail.

All thirteen archetypes headed their mandate `# Task: <title>` until `1c53592`.
That is not the `task` heading `parse_task_file` recognises, so every one of
them built an empty requirement registry, `decompose` correctly made no call
over no requirements, and `decomposition_accuracy` scored the nothing that came
back. No test failed, because the doubles supplied obligations the real code
could never have produced from that input.

`1c53592` reshaped the corpus and closed the instance. These tests close the
mechanism: **a case that produces no requirements is not a case that scores
zero, it is a case that did not run**, and it has to say so.

The corpus cannot demonstrate that. Every task file in it parses to a non-empty
registry today — which is the point of the fix, and the reason the firing tests
below supply their own unreadable task file rather than reaching for a fixture.
A guard tested against a corpus that is currently good is a guard tested against
nothing.

No model calls are made here. The guard is a parse, not a judgement.
"""

import json
from pathlib import Path

import pytest

from acceptance.benchmark.case import (
    EmptyRequirementRegistryError,
    require_nonempty_registry,
)
from acceptance.benchmark.corpus import (
    build_corpus_case,
    build_decompose_case,
    load_decompose_meta,
)
from acceptance.benchmark.fixtures import build_benchmark_case

REPO = Path(__file__).resolve().parents[2]
ARCHETYPES_DIR = REPO / "tests" / "fixtures" / "archetypes"
DECOMPOSE_CASES_DIR = REPO / "tests" / "fixtures" / "decompose-regression"

ARCHETYPE_DIRS = sorted(p for p in ARCHETYPES_DIR.iterdir() if p.is_dir())
DECOMPOSE_CASE_DIRS = sorted(p for p in DECOMPOSE_CASES_DIR.iterdir() if p.is_dir())

# The exact shape of the #228 defect: a mandate that reads perfectly well and
# parses to nothing. `# Task: <title>` lowercases to `task: add csv export`,
# which is not the `task` heading, so the paragraph lands in `unclaimed`.
UNREADABLE_TASK = "# Task: add CSV export\n\nAdd CSV export with active filters.\n"

READABLE_TASK = "# Task\nAdd CSV export with active filters.\n"


def test_a_task_file_with_requirements_passes():
    require_nonempty_registry("some-case", READABLE_TASK)


def test_a_task_file_with_no_requirements_raises_naming_the_case():
    with pytest.raises(EmptyRequirementRegistryError) as excinfo:
        require_nonempty_registry("01-missed-obligation", UNREADABLE_TASK)

    assert "01-missed-obligation" in str(excinfo.value)


def test_the_error_says_the_case_did_not_run_rather_than_scored_zero():
    """The distinction #228 turns on, asserted on the message itself.

    A reader who sees only "empty registry" has no reason to treat the run
    differently from a bad one. The message has to rule out the reading that a
    metric of 0.0 would invite.
    """
    with pytest.raises(EmptyRequirementRegistryError) as excinfo:
        require_nonempty_registry("some-case", UNREADABLE_TASK)

    message = str(excinfo.value)
    assert "did not run" in message
    assert "not a score of zero" in message


def test_the_guard_is_the_real_parse_not_a_heading_check():
    """An unrecognised heading is not the only way to reach an empty registry.

    A file with recognised section headings and no bullets under them parses
    fine and still yields nothing, so a guard that looked for `# Task` would
    pass it. This is the case a proxy check would miss.
    """
    with pytest.raises(EmptyRequirementRegistryError):
        require_nonempty_registry("some-case", "## Constraints\n\n## Scope exclusions\n")


def test_an_archetype_case_cannot_be_built_from_an_unreadable_task_file(tmp_path):
    fixture_dir = tmp_path / "99-unreadable"
    fixture_dir.mkdir()
    (fixture_dir / "task.md").write_text(UNREADABLE_TASK)

    with pytest.raises(EmptyRequirementRegistryError) as excinfo:
        build_benchmark_case(fixture_dir, tmp_path / "repo")

    assert "99-unreadable" in str(excinfo.value)


def test_an_archetype_case_fails_before_it_materializes_a_repo(tmp_path):
    """The guard runs first, so no two-commit repo is built for a dead case.

    Also what makes the test above meaningful: the fixture directory has only a
    `task.md`, no `meta.json`, no `base/` and no `head/`. If the guard ran after
    materialization the builder would raise something else entirely.
    """
    fixture_dir = tmp_path / "99-unreadable"
    fixture_dir.mkdir()
    (fixture_dir / "task.md").write_text(UNREADABLE_TASK)
    dest = tmp_path / "repo"

    with pytest.raises(EmptyRequirementRegistryError):
        build_benchmark_case(fixture_dir, dest)

    assert not dest.exists()


def test_a_decompose_case_cannot_be_built_from_an_unreadable_task_file(tmp_path):
    run_dir = tmp_path / "runs" / "999-gate1-run1"
    run_dir.mkdir(parents=True)
    (run_dir / "current-task.md").write_text(UNREADABLE_TASK)

    case_dir = tmp_path / "999-unreadable"
    case_dir.mkdir()
    (case_dir / "case.json").write_text(
        json.dumps(
            {
                "run": "999-gate1-run1",
                "run_dir": "runs/999-gate1-run1",
                "judgement": "synthetic",
                "summary": "synthetic",
            }
        )
    )

    with pytest.raises(EmptyRequirementRegistryError) as excinfo:
        build_decompose_case(case_dir, tmp_path)

    assert "999-unreadable" in str(excinfo.value)


def test_a_corpus_case_cannot_be_built_from_an_unreadable_task_file(tmp_path):
    """The rating-stability builder is guarded too.

    Beyond the two corpora #228 names, and deliberately: an unreadable task file
    costs a `check` case more than a `decompose` one, because every stage after
    decomposition runs over no obligations and reports that it found nothing
    wrong. `repo` is never touched — the guard raises before materialization.
    """
    corpus_root = tmp_path / "corpus"
    (corpus_root / "999-gate2-run1").mkdir(parents=True)
    (corpus_root / "999-gate2-run1" / "current-task.md").write_text(UNREADABLE_TASK)

    case_dir = tmp_path / "999-unreadable"
    case_dir.mkdir()
    (case_dir / "case.json").write_text(
        json.dumps(
            {
                "corpus_run": "999-gate2-run1",
                "base_revision": "HEAD",
                "head_revision": "HEAD",
                "judgement": "synthetic",
                "summary": "synthetic",
            }
        )
    )

    with pytest.raises(EmptyRequirementRegistryError) as excinfo:
        build_corpus_case(case_dir, REPO, corpus_root, tmp_path / "wt")

    assert "999-unreadable" in str(excinfo.value)


@pytest.mark.parametrize("fixture_dir", ARCHETYPE_DIRS, ids=lambda p: p.name)
def test_every_archetype_task_file_yields_requirements(fixture_dir):
    require_nonempty_registry(fixture_dir.name, (fixture_dir / "task.md").read_text())


@pytest.mark.parametrize("case_dir", DECOMPOSE_CASE_DIRS, ids=lambda p: p.name)
def test_every_decompose_regression_task_file_yields_requirements(case_dir):
    meta = load_decompose_meta(case_dir)
    require_nonempty_registry(case_dir.name, (REPO / meta.run_dir / "current-task.md").read_text())


def test_both_corpora_are_actually_covered():
    """Guards the guard: the two parametrized tests above pass vacuously if
    their corpus directory is empty or moves, which is the failure mode #228 is
    about in the first place — a suite that shrinks without saying so."""
    assert len(ARCHETYPE_DIRS) == 13
    assert len(DECOMPOSE_CASE_DIRS) == 8
