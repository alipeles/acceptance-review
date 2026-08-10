"""M-B5a.1 acceptance: each archetype fixture builds, has a non-empty
base->head diff, and its pytest suite runs with the intended outcome.

The nine numbered archetypes are the §13.5 #1-9 demonstration scenarios; each
embodies a plausible mistake a capable coding agent could actually make,
hidden behind a green test suite — which is exactly what the checker must
learn to catch. M3.5.4 adds three **sibling** archetypes to #8 (DR-081): they
share its scenario number (8) but a distinct `name`, one per unrequested-change
disposition (in_service / separable / risky) that #8 alone doesn't cover.
"""

import json
import os
import subprocess
import sys
from contextlib import contextmanager
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

# The #8 siblings (M3.5.4/DR-081): one archetype per unrequested-change
# disposition #8 alone doesn't demonstrate. `-test-support` (#139) covers the
# case that recurred across #122/#126/#139 — test scaffolding a source change
# in the same diff requires, which is in_service rather than separable.
EXPECTED_SIBLING_NAMES = {
    "08-unrequested-change-in-service",
    "08-unrequested-change-separable",
    "08-unrequested-change-risky-adjacent",
    "08-unrequested-change-test-support",
}


def test_all_expected_archetypes_are_present():
    assert {p.name for p in FIXTURE_DIRS} == EXPECTED_NAMES | EXPECTED_SIBLING_NAMES


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


def _committed_files(repo: Path, sha: str) -> dict[str, bytes]:
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", sha],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    return {
        name: subprocess.run(
            ["git", "show", f"{sha}:{name}"],
            cwd=repo,
            check=True,
            capture_output=True,
        ).stdout
        for name in listing
    }


def _fixture_files(tree: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(tree)): p.read_bytes()
        for p in sorted(tree.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}
    }


def test_each_commit_records_the_fixture_tree_verbatim(fixture_dir, tmp_path):
    """Both commits must hold exactly the fixture's own files, byte for byte.

    Stable SHAs alone do not say the SHAs are *right*: a materialization that
    consistently committed the wrong blob would satisfy the determinism test and
    still hand the benchmark a repo whose head does not contain the change under
    review. This pins content, so the two together mean reproducible *and*
    faithful.
    """
    fixture = materialize_archetype(fixture_dir, tmp_path / "repo")

    for stage, sha in (("base", fixture.base_sha), ("head", fixture.head_sha)):
        assert _committed_files(fixture.repo_path, sha) == _fixture_files(fixture_dir / stage), (
            f"{stage} commit does not match {fixture_dir.name}/{stage}"
        )


def _write_fixture(root: Path, base: dict[str, bytes], head: dict[str, bytes]) -> Path:
    """A minimal archetype whose base and head files can be dictated exactly."""
    for stage, files in (("base", base), ("head", head)):
        (root / stage).mkdir(parents=True)
        for name, content in files.items():
            (root / stage / name).write_bytes(content)
    (root / "meta.json").write_text(
        json.dumps(
            {"scenario": 0, "name": "synthetic", "intended_pytest": "pass", "summary": "synthetic"}
        )
    )
    return root


def _same_size_replacement_fixture(root: Path) -> Path:
    """The shape that broke: a file replaced by same-size content, plus an added
    file so the head commit is non-empty either way — a stale blob then shows up
    as wrong content rather than as a failure to commit, which is #234's exact
    signature."""
    return _write_fixture(
        root,
        base={"mod.py": b"VALUE = 1\n"},
        head={"mod.py": b"VALUE = 2\n", "test_mod.py": b"from mod import VALUE\n"},
    )


def _stamp(fixture: Path, stage: str, when: int) -> None:
    for path in sorted((fixture / stage).iterdir()):
        os.utime(path, (when, when))


# git comparing a working-tree file against its recorded status on fewer fields:
# size, mode and mtime only — the three `shutil.copy2` faithfully preserves.
FEWER_STAT_FIELDS = {
    "GIT_CONFIG_COUNT": "2",
    "GIT_CONFIG_KEY_0": "core.checkStat",
    "GIT_CONFIG_VALUE_0": "minimal",
    "GIT_CONFIG_KEY_1": "core.trustctime",
    "GIT_CONFIG_VALUE_1": "false",
}


@contextmanager
def _git_env(overrides: dict[str, str]):
    """Apply git config env vars to the subprocesses materialization spawns."""
    previous = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_head_content_wins_when_the_replacement_has_matching_metadata(tmp_path, monkeypatch):
    """A head file the same size, mode and mtime as the base file it replaces
    must still be committed with its head content.

    `git add` skips re-reading a file whose cached stat data is unchanged, and
    `shutil.copy2` preserves both mtime and mode — so size is the only field
    left to give the replacement away. `core.checkStat=minimal` with
    `core.trustctime=false` is git comparing exactly those fields, which is what
    a CI runner did in #234: the head commit silently kept the base blob and
    `head_sha` differed between two materializations of one fixture.

    Forcing that comparison makes the failure deterministic on any platform
    rather than something that surfaces once every few CI runs.
    """
    fixture = _same_size_replacement_fixture(tmp_path / "fixture")
    _stamp(fixture, "base", 1_600_000_000)
    _stamp(fixture, "head", 1_600_000_000)  # identical mtime across the replacement

    for key, value in FEWER_STAT_FIELDS.items():
        monkeypatch.setenv(key, value)

    materialized = materialize_archetype(fixture, tmp_path / "repo")

    committed = _committed_files(materialized.repo_path, materialized.head_sha)
    assert committed == {"mod.py": b"VALUE = 2\n", "test_mod.py": b"from mod import VALUE\n"}


def test_modification_times_do_not_change_what_is_committed(tmp_path):
    """Materializing the same files must record the same commits no matter what
    mtimes they carry on disk.

    Two materializations of one fixture, differing only in whether the head
    files share the base files' mtime. Nothing about the *content* differs, so
    nothing about the commits may differ. An implementation that lets git decide
    from cached stat data fails here: the run whose mtimes collide reuses the
    base blob, the run whose mtimes differ does not, and the two disagree on
    `head_sha` — which is how #234 presented, one archetype flipping between two
    values across runs.
    """
    collided = _same_size_replacement_fixture(tmp_path / "collided")
    _stamp(collided, "base", 1_600_000_000)
    _stamp(collided, "head", 1_600_000_000)

    distinct = _same_size_replacement_fixture(tmp_path / "distinct")
    _stamp(distinct, "base", 1_600_000_000)
    _stamp(distinct, "head", 1_600_000_500)

    with _git_env(FEWER_STAT_FIELDS):
        first = materialize_archetype(collided, tmp_path / "a")
        second = materialize_archetype(distinct, tmp_path / "b")

    assert first.base_sha == second.base_sha
    assert first.head_sha == second.head_sha
    assert _committed_files(first.repo_path, first.head_sha) == _committed_files(
        second.repo_path, second.head_sha
    )


def test_recorded_commits_survive_git_comparing_fewer_status_fields(tmp_path):
    """What gets committed must not depend on how git is configured to compare a
    working-tree file against its recorded status.

    `core.checkStat=minimal` and `core.trustctime=false` narrow that comparison
    to size, mode and mtime — the fields `shutil.copy2` preserves, so a same-size
    replacement can match on all three. Materialization must record the same
    commits under that configuration as under git's default one; if it does not,
    its output depends on the machine it ran on rather than on the fixture.
    """
    fixture = _same_size_replacement_fixture(tmp_path / "fixture")
    _stamp(fixture, "base", 1_600_000_000)
    _stamp(fixture, "head", 1_600_000_000)

    default = materialize_archetype(fixture, tmp_path / "default")
    with _git_env(FEWER_STAT_FIELDS):
        fewer_fields = materialize_archetype(fixture, tmp_path / "fewer")

    assert default.base_sha == fewer_fields.base_sha
    assert default.head_sha == fewer_fields.head_sha
    assert _committed_files(fewer_fields.repo_path, fewer_fields.head_sha) == {
        "mod.py": b"VALUE = 2\n",
        "test_mod.py": b"from mod import VALUE\n",
    }


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


def test_materialization_ignores_compiled_python(tmp_path):
    """The same fixture must materialize to the same SHA whether or not its
    modules have been imported.

    `__pycache__` is untracked build output that appears only once something
    compiles the fixture's sources, so including it made the determinism
    guarantee depend on test ordering — a fresh clone and a clone that had run
    the suite once produced different SHAs. It broke CI on main exactly that way.
    """
    import shutil

    fixture = ARCHETYPES_DIR / "07-declaration-mismatch"
    for cache in list(fixture.rglob("__pycache__")):
        shutil.rmtree(cache)
    without = materialize_archetype(fixture, tmp_path / "without").head_sha

    cache_dir = fixture / "head" / "__pycache__"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "user_lookup.cpython-310.pyc").write_bytes(b"\x00compiled\x00")
    try:
        with_cache = materialize_archetype(fixture, tmp_path / "with").head_sha
    finally:
        shutil.rmtree(cache_dir)

    assert with_cache == without
