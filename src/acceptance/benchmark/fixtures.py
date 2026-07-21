"""Archetype fixture materialization (M-B5a.1).

The archetype scenarios (§13.5 #1–9) are hand-built ground truth: each is a
tiny task + a base/head change embodying one way a *plausible* review can go
wrong — the kind of mistake a capable coding agent actually makes, not a
strawman. They can't be stored as real nested git repos (git won't track a
nested .git), so each is kept as reviewable source trees under
`tests/fixtures/archetypes/<NN-name>/`:

    task.md          the change mandate (the checker's task-file input)
    declaration.md   optional builder declaration (only where an archetype needs one)
    base/            source tree before the change
    head/            source tree after the change (implementation + tests)
    meta.json        scenario number, name, intended pytest outcome, summary

`materialize_archetype` turns one of those into a real two-commit git repo on
demand, which is exactly the shape M-B0.2's runner consumes (repo +
base/head revisions). Commit timestamps are fixed, so the same fixture always
materializes to the same base/head SHAs — reproducible, in the spirit of M0.5.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from acceptance.model_base import PersistableModel

# Fixed identity + timestamps so materialization is deterministic (stable SHAs).
_FIXTURE_NAME = "Archetype Fixtures"
_FIXTURE_EMAIL = "fixtures@example.com"
_FIXTURE_DATE = "2020-01-02T03:04:05+00:00"


class ArchetypeMeta(PersistableModel):
    scenario: int
    name: str
    intended_pytest: Literal["pass", "fail"]
    summary: str


@dataclass(frozen=True)
class MaterializedFixture:
    repo_path: Path
    base_sha: str
    head_sha: str
    meta: ArchetypeMeta


def load_meta(fixture_dir: Path) -> ArchetypeMeta:
    import json

    return ArchetypeMeta.from_dict(json.loads((fixture_dir / "meta.json").read_text()))


def materialize_archetype(fixture_dir: Path, dest: Path) -> MaterializedFixture:
    """Build a two-commit git repo (base then head) from a fixture directory."""
    meta = load_meta(fixture_dir)
    repo = dest
    repo.mkdir(parents=True, exist_ok=True)

    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", _FIXTURE_NAME)
    _git(repo, "config", "user.email", _FIXTURE_EMAIL)

    _replace_worktree(repo, fixture_dir / "base")
    _git(repo, "add", "-A")
    _commit(repo, "base")
    base_sha = _rev_parse(repo, "HEAD")

    _replace_worktree(repo, fixture_dir / "head")
    _git(repo, "add", "-A")
    _commit(repo, "head")
    head_sha = _rev_parse(repo, "HEAD")

    return MaterializedFixture(repo_path=repo, base_sha=base_sha, head_sha=head_sha, meta=meta)


def _replace_worktree(repo: Path, tree: Path) -> None:
    """Clear the working tree (keeping .git) and copy `tree` into it, so a
    file removed between base and head is staged as a deletion by `git add -A`."""
    for entry in repo.iterdir():
        if entry.name == ".git":
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    shutil.copytree(tree, repo, dirs_exist_ok=True)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


def _commit(repo: Path, message: str) -> None:
    env_dates = {"GIT_AUTHOR_DATE": _FIXTURE_DATE, "GIT_COMMITTER_DATE": _FIXTURE_DATE}
    subprocess.run(
        ["git", "commit", "-q", "-m", message],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={**_os_environ(), **env_dates},
    )


def _rev_parse(repo: Path, revision: str) -> str:
    return _git(repo, "rev-parse", revision).stdout.strip()


def _os_environ() -> dict:
    import os

    return dict(os.environ)
