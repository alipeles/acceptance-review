import subprocess
from pathlib import Path

import pytest


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _rev_parse(repo: Path, revision: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", revision], cwd=repo, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")

    (repo / "file.txt").write_text("v1\n")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-q", "-m", "base")
    base_sha = _rev_parse(repo, "HEAD")

    (repo / "file.txt").write_text("v2\n")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-q", "-m", "head")
    head_sha = _rev_parse(repo, "HEAD")

    monkeypatch.chdir(repo)
    return {"path": repo, "base": base_sha, "head": head_sha}


@pytest.fixture
def fixture_task_path():
    return str(Path(__file__).parent / "fixtures" / "tasks" / "minimal_task.md")
