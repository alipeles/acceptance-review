"""M-B5a.1 acceptance: each archetype fixture builds, has a non-empty
base->head diff, and its pytest suite runs with the intended outcome.

The nine archetypes are the §13.5 #1-9 demonstration scenarios; each embodies
a plausible mistake a capable coding agent could actually make, hidden behind
a green test suite — which is exactly what the checker must learn to catch.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from acceptance.benchmark.fixtures import load_meta, materialize_archetype

ARCHETYPES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"

FIXTURE_DIRS = sorted(p for p in ARCHETYPES_DIR.iterdir() if p.is_dir())

EXPECTED_NAMES = {
    "01-missed-obligation",
    "02-qualifier-missed",
    "03-superficial-test",
    "04-non-discriminating-input",
    "05-circular-expected-result",
    "06-mocked-out-behavior",
    "07-declaration-mismatch",
    "08-unrequested-change",
    "09-revision-cycle",
}


def test_all_nine_archetypes_are_present():
    assert {p.name for p in FIXTURE_DIRS} == EXPECTED_NAMES


@pytest.fixture(params=FIXTURE_DIRS, ids=lambda p: p.name)
def fixture_dir(request):
    return request.param


def test_fixture_has_task_and_meta(fixture_dir):
    assert (fixture_dir / "task.md").is_file()
    assert (fixture_dir / "base").is_dir()
    assert (fixture_dir / "head").is_dir()
    meta = load_meta(fixture_dir)
    assert f"{meta.scenario:02d}-{meta.name}" == fixture_dir.name


def test_materializes_with_a_non_empty_diff(fixture_dir, tmp_path):
    fixture = materialize_archetype(fixture_dir, tmp_path / "repo")

    assert fixture.base_sha != fixture.head_sha
    diff = subprocess.run(
        ["git", "diff", "--name-only", fixture.base_sha, fixture.head_sha],
        cwd=fixture.repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert diff.stdout.strip(), "git diff base head must be non-empty"


def test_materialization_is_deterministic(fixture_dir, tmp_path):
    first = materialize_archetype(fixture_dir, tmp_path / "a")
    second = materialize_archetype(fixture_dir, tmp_path / "b")

    # Fixed identity + commit dates => stable SHAs across materializations.
    assert first.base_sha == second.base_sha
    assert first.head_sha == second.head_sha


def test_head_pytest_runs_with_the_intended_outcome(fixture_dir, tmp_path):
    fixture = materialize_archetype(fixture_dir, tmp_path / "repo")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=fixture.repo_path,
        capture_output=True,
        text=True,
    )

    if fixture.meta.intended_pytest == "pass":
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, result.stdout + result.stderr
