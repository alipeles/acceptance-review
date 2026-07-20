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


def _make_git_repo(repo: Path) -> dict:
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

    return {"path": repo, "base": base_sha, "head": head_sha}


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    info = _make_git_repo(tmp_path / "repo")
    monkeypatch.chdir(info["path"])
    return info


@pytest.fixture
def git_repo_elsewhere(tmp_path):
    """A git repo the test process is NOT chdir'd into — proves callers that
    pass an explicit repo path don't depend on the current working directory."""
    return _make_git_repo(tmp_path / "repo")


@pytest.fixture
def fixture_task_path():
    return str(Path(__file__).parent / "fixtures" / "tasks" / "minimal_task.md")
