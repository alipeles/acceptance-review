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


@pytest.fixture
def stub_model(monkeypatch):
    """Make `main()`'s internally-built client a no-op stub.

    Since M7.4 `acceptance check` runs the real shared pipeline, so CLI tests
    that exercise plumbing (provenance, persistence, determinism, the §16
    shell) rather than model judgment must not issue live calls. Patching
    RunConfig.build_client keeps `main()`'s own argument parsing under test.

    The stub stands in for the *network*, not for the configuration: it carries
    the config's own model and determinism controls, so a CLI test can still
    assert that a flag reaches the review's provenance (#160 sources provenance
    from the client, so a stub that ignored the config would silently break that
    link). Its mode is necessarily RECORD — see `client_dispatching`.
    """
    from acceptance.config import RunConfig
    from tests.support import client_finding_nothing

    monkeypatch.setattr(
        RunConfig,
        "build_client",
        lambda self, completion_fn=None: client_finding_nothing(
            model=self.model, temperature=self.temperature, seed=self.seed
        ),
    )
