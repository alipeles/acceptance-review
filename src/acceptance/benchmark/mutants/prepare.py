"""Fetch what a label build needs: the network half of #372, run once by hand.

For each pinned bug it downloads the project at the fix commit and the fix
commit's message (the case's requirement text, decided at #372's Gate 1). For
each project it builds one environment with `uv`, resolving the pinned package
names against a fixed date so the same names always give the same versions.

The build itself (`build.py`) is offline and runs every test in the sandbox.
Keeping the network here, in a step a person starts, is what lets the build
stay inside it.

Every step is skipped when its output already exists, so a rerun only fetches
what is missing. Everything lands under the gitignored `.acceptance/mutant-labels/`.
"""

from __future__ import annotations

import email
import io
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

from acceptance.benchmark.mutants.bugsinpy import BugInfo, PinnedBugs, read_bug

__all__ = ["LabelPaths", "prepare"]

_USER_AGENT = "acceptance-tool mutant-label prepare (#372)"


class LabelPaths:
    """Where every artifact of a build lives, under one gitignored root."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.dataset = root / "src" / "BugsInPy-master"
        self.projects = root / "projects"
        self.messages = root / "messages"
        self.envs = root / "envs"
        self.labels = root / "labels.json"
        self.sample = root / "survivor-sample.json"

    def checkout(self, bug: BugInfo) -> Path:
        return self.projects / f"{bug.project}-{bug.bug_id}"

    def message(self, bug: BugInfo) -> Path:
        return self.messages / f"{bug.project}-{bug.bug_id}.txt"

    def interpreter(self, project: str) -> Path:
        return self.envs / project / "bin" / "python"


def prepare(pins: PinnedBugs, paths: LabelPaths, log=print) -> list[str]:
    """Fetch every pinned bug and build every project environment.

    Returns the problems met, one line each; a bug that cannot be fetched is
    reported and skipped rather than stopping the others.
    """
    problems: list[str] = []
    for project, packages in sorted(pins.projects.items()):
        try:
            _environment(project, packages, pins, paths, log)
        except (OSError, subprocess.CalledProcessError) as error:
            problems.append(f"{project}: environment failed: {error}")
    for key in pins.bugs:
        try:
            bug = read_bug(paths.dataset, key)
            _checkout(bug, paths, log)
            _message(bug, paths, log)
        except (OSError, KeyError, tarfile.TarError) as error:
            problems.append(f"{key}: {error}")
    for line in problems:
        log(f"PROBLEM {line}")
    return problems


def _environment(
    project: str, packages: list[str], pins: PinnedBugs, paths: LabelPaths, log
) -> None:
    interpreter = paths.interpreter(project)
    if interpreter.exists():
        return
    log(f"env {project}: {' '.join(packages)}")
    env_dir = paths.envs / project
    subprocess.run(["uv", "venv", "--python", pins.python, str(env_dir)], check=True)
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(interpreter),
            "--exclude-newer",
            pins.exclude_newer,
            *packages,
        ],
        check=True,
    )


def _checkout(bug: BugInfo, paths: LabelPaths, log) -> None:
    target = paths.checkout(bug)
    if target.exists():
        return
    owner_repo = bug.github_url.removeprefix("https://github.com/")
    url = f"https://codeload.github.com/{owner_repo}/tar.gz/{bug.fixed_commit}"
    log(f"fetch {bug.key} @ {bug.fixed_commit[:10]}")
    data = _get(url)
    staging = target.with_name(target.name + ".partial")
    shutil.rmtree(staging, ignore_errors=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = archive.getmembers()
        prefix = members[0].name.split("/")[0] + "/"
        for member in members:
            # Checked by hand rather than with `filter="data"`, which the 3.10.11
            # interpreter this repo runs on predates.
            if not member.name.startswith(prefix) or not (member.isfile() or member.isdir()):
                continue
            member.name = member.name[len(prefix) :]
            if not member.name or member.name.startswith("/") or ".." in member.name.split("/"):
                continue
            archive.extract(member, staging)
    staging.rename(target)


def _message(bug: BugInfo, paths: LabelPaths, log) -> None:
    target = paths.message(bug)
    if target.exists():
        return
    log(f"message {bug.key}")
    patch = _get(f"{bug.github_url}/commit/{bug.fixed_commit}.patch").decode("utf-8", "replace")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(commit_message(patch), encoding="utf-8")


def commit_message(patch: str) -> str:
    """The subject and body of a `git format-patch` email, without the diff."""
    message = email.message_from_string(patch)
    subject = " ".join((message.get("Subject") or "").split())
    if subject.startswith("[PATCH"):
        subject = subject.split("]", 1)[1].strip()
    payload = message.get_payload()
    body = payload if isinstance(payload, str) else ""
    body = body.split("\n---\n", 1)[0].strip()
    return f"{subject}\n\n{body}".strip() + "\n"


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()
