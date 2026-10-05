"""Reading BugsInPy's per-bug metadata, and the pinned bug list (#372).

BugsInPy holds, per bug, `bug.info` (the buggy and fixed commits and the test
file), `bug_patch.txt` (the fix as a unified diff) and `run_test.sh` (the
command that shows the bug). Mutants are placed only on the lines the fix
changed, read from the patch's new side, so every edit lands in code a real
bug lived in.

This module reads files and parses text; it fetches nothing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import Field

from acceptance.model_base import PersistableModel

__all__ = [
    "BugInfo",
    "PinnedBugs",
    "fix_lines",
    "load_pinned_bugs",
    "read_bug",
    "trigger_test_ids",
]

#: The committed pin. Bug ids and a dataset commit are not derived content, so
#: this file is safe to commit where the labels are not (DR-168).
PINNED_BUGS = Path(__file__).with_name("pinned_bugs.json")

_INFO_FIELD = re.compile(r'^\s*(\w+)\s*=\s*"([^"]*)"', re.MULTILINE)
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class PinnedBugs(PersistableModel):
    """Which bugs a build uses, and how, fixed so a rebuild reproduces the file.

    `bugsinpy_commit` pins the dataset. `projects` maps a project to the
    packages its tests need, installed into one environment per project.
    `exclude_newer` is the resolution cutoff for those packages, so the same
    names always resolve to the same versions.
    """

    bugsinpy_commit: str
    python: str
    exclude_newer: str
    tests_per_bug: int = Field(ge=1)
    mutants_per_bug: int = Field(ge=1)
    projects: dict[str, list[str]]
    bugs: list[str]


class BugInfo(PersistableModel):
    project: str
    bug_id: int
    github_url: str
    buggy_commit: str
    fixed_commit: str
    test_file: str
    run_test: str
    patch: str

    @property
    def key(self) -> str:
        return f"{self.project}/{self.bug_id}"


def load_pinned_bugs(path: Path = PINNED_BUGS) -> PinnedBugs:
    return PinnedBugs.from_dict(json.loads(path.read_text(encoding="utf-8")))


def read_bug(dataset: Path, key: str) -> BugInfo:
    """Read one bug, `project/<n>`, from an unpacked BugsInPy checkout."""
    project, number = key.split("/")
    bug_dir = dataset / "projects" / project / "bugs" / number
    info = dict(_INFO_FIELD.findall((bug_dir / "bug.info").read_text(encoding="utf-8")))
    project_info = dict(
        _INFO_FIELD.findall((dataset / "projects" / project / "project.info").read_text("utf-8"))
    )
    return BugInfo(
        project=project,
        bug_id=int(number),
        github_url=project_info["github_url"].rstrip("/"),
        buggy_commit=info["buggy_commit_id"],
        fixed_commit=info["fixed_commit_id"],
        test_file=info["test_file"].split(";")[0],
        run_test=(bug_dir / "run_test.sh").read_text(encoding="utf-8", errors="replace"),
        patch=(bug_dir / "bug_patch.txt").read_text(encoding="utf-8", errors="replace"),
    )


def fix_lines(patch: str) -> dict[str, set[int]]:
    """Per non-test Python file, the new-side lines the fix added or changed.

    A hunk that only deletes contributes the new-side line where the deletion
    happened, so a fix that removes a wrong line still marks a place to mutate.
    """
    lines: dict[str, set[int]] = {}
    path: str | None = None
    new_line = 0
    pending_deletion = False
    for raw in patch.splitlines():
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            target = target.removeprefix("b/")
            path = target if _is_source(target) else None
            continue
        if raw.startswith(("--- ", "diff ")):
            continue
        match = _HUNK.match(raw)
        if match:
            new_line = int(match.group(1))
            pending_deletion = False
            continue
        if path is None:
            continue
        if raw.startswith("+"):
            lines.setdefault(path, set()).add(new_line)
            new_line += 1
            pending_deletion = False
        elif raw.startswith("-"):
            pending_deletion = True
        else:
            if pending_deletion:
                lines.setdefault(path, set()).add(max(new_line - 1, 1))
                lines.setdefault(path, set()).add(new_line)
                pending_deletion = False
            new_line += 1
    return lines


def trigger_test_ids(run_test: str) -> list[str]:
    """The pytest node ids `run_test.sh` names, whether it calls pytest or unittest."""
    ids: list[str] = []
    for line in run_test.splitlines():
        words = line.split()
        if not words:
            continue
        # `python`, `python3`, `python3.7` … all launch the same module runner.
        launched = words[0].startswith("python") and words[1:2] == ["-m"] and len(words) > 2
        module = words[2] if launched else None
        if words[0] in {"pytest", "py.test"} or module == "pytest":
            ids.extend(w for w in words if "::" in w or w.endswith(".py"))
        elif module == "unittest":
            ids.extend(_unittest_to_node(w) for w in words[3:] if not w.startswith("-"))
    return list(dict.fromkeys(i for i in ids if i))


def _unittest_to_node(dotted: str) -> str:
    """`test.test_utils.TestUtil.test_x` -> `test/test_utils.py::TestUtil::test_x`."""
    parts = dotted.split(".")
    # The module path ends just before the first capitalised segment, the class.
    for index, part in enumerate(parts):
        if part[:1].isupper():
            return "/".join(parts[:index]) + ".py::" + "::".join(parts[index:])
    return "/".join(parts) + ".py"


def _is_source(path: str) -> bool:
    if not path.endswith(".py"):
        return False
    pieces = path.split("/")
    name = pieces[-1]
    if any(p in {"test", "tests", "testing"} for p in pieces[:-1]):
        return False
    return not (name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py")
