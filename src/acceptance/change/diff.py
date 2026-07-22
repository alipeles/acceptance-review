"""Revision & diff extraction (M2.1) and working-tree mode (M2.3, §5.1).

Extracts the structural Git change set between two revisions — or between a
base revision and the current working tree, so the checker works before a PR
or commit exists — into the same shape: which files changed, how (added/
modified/deleted/renamed), what they are (source/test/config/other), and
their hunk-level diffs. Pure `git` plumbing — no LLM call, since this is
structural, not semantic (§13.3 Git change analysis).

Working-tree mode limitation: `git diff` never shows untracked files, so they
are detected separately (`git ls-files --others`) and read directly rather
than diffed. This means a rename done via plain `mv` (not staged with
`git mv`) is seen as a deletion plus a separate untracked addition, not a
rename — untracked files can't participate in git's similarity-based rename
detection. A staged rename (`git mv`, or `mv` + `git add`) is detected
correctly, same as a committed one.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from acceptance.review_state import ChangeSet, DiffHunk, FileChange

WORKING_TREE_SENTINEL = "<working-tree>"

_TEST_PATH_RE = re.compile(r"(^|/)tests?/|(^|/)test_[^/]+\.py$|_test\.py$")
_CONFIG_NAMES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "tox.ini",
}
_CONFIG_SUFFIXES = (".lock",)

_STATUS_MAP = {"A": "added", "M": "modified", "D": "deleted"}

_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_lines>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_lines>\d+))? @@.*$"
)


def extract_change_set(repo: Path, base: str, head: str) -> ChangeSet:
    """Extract the structural change set between `base` and `head` in `repo`."""
    entries = _parse_name_status(_git(repo, "diff", "--name-status", "-M", base, head))
    blocks = _split_file_blocks(_git(repo, "diff", "-U3", base, head))
    return ChangeSet(
        base_revision=base, head_revision=head, files=_build_files(entries, blocks)
    )


def extract_working_tree_change_set(repo: Path, base: str) -> ChangeSet:
    """Extract the change set between `base` and the current working tree
    (staged + unstaged + untracked) — no head commit required (§5.1)."""
    entries = _parse_name_status(_git(repo, "diff", "--name-status", "-M", base))
    blocks = _split_file_blocks(_git(repo, "diff", "-U3", base))
    files = _build_files(entries, blocks) + _untracked_file_changes(repo)
    return ChangeSet(base_revision=base, head_revision=WORKING_TREE_SENTINEL, files=files)


def _build_files(entries: list[dict], blocks: dict[str, str]) -> list[FileChange]:
    return [
        FileChange(
            path=entry["path"],
            status=entry["status"],
            category=_categorize(entry["path"]),
            old_path=entry["old_path"],
            hunks=_parse_hunks(blocks.get(entry["path"]) or blocks.get(entry["old_path"]) or ""),
        )
        for entry in entries
    ]


def _untracked_file_changes(repo: Path) -> list[FileChange]:
    """Untracked files as synthetic all-added FileChanges — git diff can't
    diff a file it doesn't know about, so these are read directly."""
    changes = []
    for path in _git(repo, "ls-files", "--others", "--exclude-standard").splitlines():
        if not path.strip():
            continue
        try:
            content = (repo / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        changes.append(
            FileChange(
                path=path,
                status="added",
                category=_categorize(path),
                hunks=_whole_file_hunk(content),
            )
        )
    return changes


def _whole_file_hunk(content: str) -> list[DiffHunk]:
    lines = content.splitlines()
    if not lines:
        return []
    return [
        DiffHunk(
            header=f"@@ -0,0 +1,{len(lines)} @@",
            old_start=0,
            old_lines=0,
            new_start=1,
            new_lines=len(lines),
            content="\n".join(f"+{line}" for line in lines),
        )
    ]


def _categorize(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    if _TEST_PATH_RE.search(path):
        return "test"
    if name in _CONFIG_NAMES or name.endswith(_CONFIG_SUFFIXES):
        return "config"
    if name.startswith("requirements") and name.endswith((".txt", ".in")):
        return "config"
    if name.endswith(".py"):
        return "source"
    return "other"


def _parse_name_status(output: str) -> list[dict]:
    entries = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        code = parts[0]
        if code.startswith("R"):
            entries.append({"status": "renamed", "path": parts[2], "old_path": parts[1]})
        else:
            entries.append(
                {"status": _STATUS_MAP.get(code[0], "modified"), "path": parts[1], "old_path": None}
            )
    return entries


def _split_file_blocks(full_diff: str) -> dict[str, str]:
    """Map each file's `diff --git` b-side path to its raw diff block text."""
    blocks: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_key is not None:
            blocks[current_key] = "\n".join(current_lines)

    for line in full_diff.splitlines():
        header = _DIFF_HEADER_RE.match(line)
        if header:
            flush()
            current_key = header.group(2)
            current_lines = [line]
        else:
            current_lines.append(line)
    flush()
    return blocks


def _parse_hunks(diff_block: str) -> list[DiffHunk]:
    hunks = []
    lines = diff_block.splitlines()
    i, n = 0, len(lines)
    while i < n:
        match = _HUNK_HEADER_RE.match(lines[i])
        if not match:
            i += 1
            continue
        header = lines[i]
        i += 1
        body: list[str] = []
        while i < n and not lines[i].startswith("@@ ") and not lines[i].startswith("diff --git "):
            body.append(lines[i])
            i += 1
        hunks.append(
            DiffHunk(
                header=header,
                old_start=int(match.group("old_start")),
                old_lines=int(match.group("old_lines") or 1),
                new_start=int(match.group("new_start")),
                new_lines=int(match.group("new_lines") or 1),
                content="\n".join(body),
            )
        )
    return hunks


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout
