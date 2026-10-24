"""A third way of building a mutation edit: a headless coding agent (#338).

The one-call builder (`descriptor.py`) sees only the lines a defect names, and
#45 traced many of its bad edits to exactly that: it cannot see the helper the
edited code calls or the argument list just past its region. Widening the
context with retrieval did not help, because retrieval returns callers, not
callees. An agent that opens files as it needs them is the version of "more
context" that had not been tried.

It is asked the same question — the smallest edit that makes one named defect
true — and its answer gets **no privileged path**. Whatever it changed in its
copy is reduced to one span replacement and handed back to the runner, which
puts it through every check any other candidate goes through. A change that is
not one contiguous span in one file is no usable answer, not something to
repair. The runner asks it only after every one-call candidate was set aside
(`runner._attempt`), because one agent run costs far more than one call.

**What is recorded is the diff, never the agent's transcript.** An agent's
account of what it did is not evidence about the code; the test run against its
edit is. The diff is recorded through `ModelClient.replay_or_run`, so a replayed
review applies it without starting the agent and two replays are identical.

**The agent cannot read the project's tests**, and that is enforced rather than
asked for. An edit aimed at what the tests do or do not catch would bias the one
observation injection exists to make — the reason `surrounding.py` withholds test
files from the one-call builder. Here the copy the agent works in has every test
file deleted, and each adapter must confine its agent to that copy by the
agent's own mechanism (see `ClaudeCodeAgent`), so the originals elsewhere on
disk are out of reach too.

**Agents are adapters.** `CodingAgent` is the whole interface: run a prompt in a
directory, under a time limit, and say whether it finished and what it cost.
Supporting another agent — Codex is the next — is one class and one entry in
`AGENTS`; the builder does not change.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import threading
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from pydantic import field_validator

from acceptance.change.diff import is_test_path
from acceptance.execution.sandbox import _terminate_group
from acceptance.llm import LLMError, ModelClient
from acceptance.model_base import PersistableModel as _Model
from acceptance.mutation.attempt import MutationDescriptor, SetAsideCandidate
from acceptance.mutation.descriptor import _earlier_candidates, _subject
from acceptance.mutation.region import Region
from acceptance.mutation.workspace import copied_project
from acceptance.review_state import Defect

__all__ = [
    "AGENTS",
    "AGENT_STAGE",
    "AgentDescriptorBuilder",
    "AgentRun",
    "AgentSettings",
    "AgentUnavailableError",
    "ClaudeCodeAgent",
    "CodingAgent",
    "agent_copy",
    "descriptor_from_changes",
    "make_agent",
]

#: The stage an agent run is recorded under, beside "mutation descriptor".
AGENT_STAGE = "mutation agent"

#: Tool configuration directories removed from the agent's copy, beside the
#: tests. A project's own agent settings can carry hooks and permission rules
#: that would run inside our agent and widen what it may do; they are the
#: project's configuration for its own sessions, not source the edit is about.
_AGENT_CONFIG_DIRS = frozenset({".claude", ".codex"})


class AgentUnavailableError(LLMError):
    """The configured agent cannot be started at all.

    Raised rather than recorded: a missing executable is a fact about this
    machine, and recording it as the agent's answer would replay "no usable
    edit" for every defect forever.
    """


@dataclass(frozen=True)
class AgentRun:
    """How one agent run ended. Its edits are read from the directory, not here."""

    finished: bool
    cost_usd: float | None
    detail: str


class CodingAgent(Protocol):
    """A headless coding agent, driven over a directory."""

    #: Recorded in each request, so two agents never share a recording.
    name: str
    #: The model the agent runs on, or None for the agent's own default.
    model: str | None

    def run(
        self, workdir: Path, prompt: str, *, forbidden: Path, timeout_seconds: float
    ) -> AgentRun:
        """Run `prompt` in `workdir` and return when it ends or the time is up.

        The agent must be able to edit files under `workdir` and must be unable
        to read or edit anything under `forbidden` — the original project, tests
        included — by its own enforcement, not by being asked.
        """
        ...


class ClaudeCodeAgent:
    """Claude Code, run as `claude -p`.

    Confined by Claude Code's own flags and nothing in the user's settings:

    - `--tools Read,Edit,Glob,Grep`: no shell, so nothing can `cat` a path the
      file tools are not allowed to open, and no tool that creates files.
    - `--settings` with a deny rule on `forbidden`, for reads and edits, and an
      allow rule for edits under the working directory only.
    - `--permission-mode dontAsk`: anything not allowed is refused instead of
      waiting for an approval nobody is there to give.

    Claude Code's sandbox setting is not used: it governs shell commands, and
    the shell is not available here at all.
    """

    name = "claude-code"

    def __init__(self, model: str | None = None, executable: str = "claude") -> None:
        self.model = model
        self.executable = executable

    def command(self, forbidden: Path) -> list[str]:
        """The command line, without the prompt, which goes on stdin."""
        # `//` starts an absolute path in a Claude Code permission rule; `./` is
        # relative to the working directory.
        absolute = f"/{forbidden.resolve()}/**"
        settings = {
            "permissions": {
                "allow": ["Read(./**)", "Edit(./**)"],
                "deny": [f"Read({absolute})", f"Edit({absolute})"],
            }
        }
        command = [
            self.executable,
            "-p",
            "--output-format",
            "json",
            "--tools",
            "Read,Edit,Glob,Grep",
            "--permission-mode",
            "dontAsk",
            "--settings",
            json.dumps(settings, sort_keys=True),
        ]
        if self.model:
            command += ["--model", self.model]
        return command

    def run(
        self, workdir: Path, prompt: str, *, forbidden: Path, timeout_seconds: float
    ) -> AgentRun:
        try:
            process = subprocess.Popen(
                self.command(forbidden),
                cwd=str(workdir),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=dict(os.environ),
                start_new_session=True,
            )
        except FileNotFoundError as error:
            raise AgentUnavailableError(
                f"the coding agent {self.name!r} could not be started: {error}. Install it, "
                "or name its executable in the agent settings."
            ) from error
        try:
            stdout, stderr = process.communicate(prompt, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_group(process)
            process.communicate()
            return AgentRun(
                finished=False,
                cost_usd=None,
                detail=f"stopped after its time limit of {timeout_seconds:g}s",
            )
        return _claude_outcome(process.returncode, stdout, stderr)


def _claude_outcome(returncode: int, stdout: str, stderr: str) -> AgentRun:
    """Read `claude -p --output-format json`'s single result object."""
    try:
        result: dict[str, Any] = json.loads(stdout)
    except json.JSONDecodeError:
        result = {}
    cost = result.get("total_cost_usd")
    cost = float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None
    if returncode != 0 or result.get("is_error") or not result:
        tail = (stderr or stdout or "").strip()[-400:]
        return AgentRun(
            finished=False,
            cost_usd=cost,
            detail=f"exited {returncode}: {tail or 'no output'}",
        )
    return AgentRun(finished=True, cost_usd=cost, detail="finished")


#: Every agent the builder can drive, by the name settings use.
AGENTS: dict[str, Callable[[str | None, str | None], CodingAgent]] = {
    "claude-code": lambda model, executable: ClaudeCodeAgent(model, executable or "claude"),
}


class AgentSettings(_Model):
    """Which agent the fallback builder drives, and under what limits.

    Absent from `ExecutionSettings` by default, and then no defect is ever sent
    to an agent and every request a review makes is the one it made before.
    """

    agent: str = "claude-code"
    model: str | None = None
    #: Unset uses the agent's usual command name.
    executable: str | None = None
    #: Per run. One that runs longer is stopped and is no usable answer.
    timeout_seconds: float = 900.0
    #: Agent runs at once. Each is a long session against a provider, so this
    #: is far below the injection pool, which is sized for cores.
    max_in_flight: int = 2

    @field_validator("agent")
    @classmethod
    def _known(cls, value: str) -> str:
        if value not in AGENTS:
            raise ValueError(f"unknown coding agent {value!r}; known: {sorted(AGENTS)}")
        return value


def make_agent(settings: AgentSettings) -> CodingAgent:
    return AGENTS[settings.agent](settings.model, settings.executable)


@contextmanager
def agent_copy(project_root: Path) -> Iterator[Path]:
    """A copy of the project with its test files and agent configuration removed.

    Tests are identified by `is_test_path`, the one shared definition the
    one-call builder's withholding uses too, so the two builders are kept from
    the same files.
    """
    with copied_project(project_root, "acceptance-agent-", link_environments=False) as root:
        for name in _AGENT_CONFIG_DIRS:
            shutil.rmtree(root / name, ignore_errors=True)
        for path in sorted(root.rglob("*"), reverse=True):
            relative = path.relative_to(root).as_posix()
            if path.is_file() and is_test_path(relative):
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                # A tests directory emptied above; leaving it would tell the
                # agent where the tests were.
                path.rmdir()
        yield root


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def _changes(root: Path, before: dict[str, str], project_root: Path) -> list[dict[str, Any]]:
    """Every file the agent changed, created or deleted, as recorded diffs.

    Each carries its unified diff (the artifact a reader inspects) and its hunks
    as span replacements against the original (what the runner can use). Line
    numbers are 1-based and inclusive; an insertion is a span whose end is one
    before its start.
    """
    after = _snapshot(root)
    changes = []
    for path in sorted(set(before) | set(after)):
        if before.get(path) == after.get(path):
            continue
        change: dict[str, Any] = {"path": path, "deleted": path not in after}
        try:
            old = (project_root / path).read_text(encoding="utf-8") if path in before else ""
            new = (root / path).read_text(encoding="utf-8") if path in after else ""
        except UnicodeDecodeError:
            change.update(binary=True, diff="", hunks=[])
            changes.append(change)
            continue
        old_lines, new_lines = old.splitlines(keepends=True), new.splitlines(keepends=True)
        change["diff"] = "".join(
            difflib.unified_diff(old_lines, new_lines, f"a/{path}", f"b/{path}")
        )
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
        change["hunks"] = [
            {"start_line": i1 + 1, "end_line": i2, "replacement": "".join(new_lines[j1:j2])}
            for tag, i1, i2, j1, j2 in matcher.get_opcodes()
            if tag != "equal"
        ]
        changes.append(change)
    return changes


def descriptor_from_changes(
    response: dict[str, Any], regions: Sequence[Region], sources: dict[str, str]
) -> MutationDescriptor | None:
    """The agent's change as one span replacement, or None when it is not one.

    None — no usable answer — when the run did not finish, changed nothing,
    changed more than one file or more than one contiguous span, deleted or
    created a file, or edited a file the defect did not name. Anything that IS
    one span is returned for the runner's checks to judge, including a span
    outside every named region: the containment check refuses it there, on the
    record, rather than here unseen.
    """
    if not response.get("finished"):
        return None
    changes = response.get("changes") or []
    if len(changes) != 1:
        return None
    change = changes[0]
    path = change.get("path")
    hunks = change.get("hunks") or []
    if change.get("deleted") or len(hunks) != 1 or path not in sources:
        return None
    lines = sources[path].splitlines(keepends=True)
    start, end = hunks[0]["start_line"], hunks[0]["end_line"]
    replacement = hunks[0]["replacement"]
    if end < start:
        # A pure insertion. A span replacement has to replace at least one
        # line, so the insertion takes the line before it with it — or the one
        # after, at the top of the file.
        if not lines:
            return None
        if start > 1:
            start = end = start - 1
            replacement = lines[start - 1] + replacement
        else:
            start = end = 1
            replacement = replacement + lines[0]
    on_path = [region for region in regions if region.path == path]
    if not on_path:
        return None
    containing = [
        region for region in on_path if region.start_line <= start and end <= region.end_line
    ]
    label = (containing or on_path)[0].label
    return MutationDescriptor(
        path=path,
        start_line=start,
        end_line=end,
        replacement=replacement,
        region_label=label,
        original="".join(lines[start - 1 : end]),
    )


_INSTRUCTIONS = """You are working in a copy of a software project. Below is ONE \
named plausible defect and the regions of the code it implicates, with line \
numbers as they are in the files right now.

Edit the files in this directory so that the defect becomes real, with the \
SMALLEST possible change: one contiguous run of lines, in one file, inside one \
of the regions listed. Read any other file you need in order to understand the \
code; edit nothing else.

The defect comes with two behaviours: EXPECTED (what the code must do) and \
DEFECTIVE (what it would do with the defect present). After your edit the \
DEFECTIVE sentence must be true of the code and the EXPECTED sentence false.

Break it the way a careless implementation would: an off-by-one, a wrong \
constant, a flipped comparison, a dropped case, a wrong unit. Do not delete the \
feature, rename anything, reformat, or fix anything else you notice. The file \
must still parse and still load.

Make NO change at all if the code already does the DEFECTIVE behaviour, if no \
single contiguous edit inside the listed regions makes the defect true, or if \
you cannot tell. Making no change is a real answer.

Only the change you leave in the files is read. Nothing you write in reply is."""


class AgentDescriptorBuilder:
    """The runner's fallback builder: one agent run per defect it is asked about.

    A `DescriptorBuilder` like the one-call builder. Its answer is a span
    replacement or None — never a decline or a claim that the code is already
    defective, because those are typed answers only a schema can carry, and
    reading them out of an agent's prose would make its account evidence.
    """

    def __init__(
        self,
        agent: CodingAgent,
        client: ModelClient,
        project_root: Path,
        timeout_seconds: float = 900.0,
        max_in_flight: int = 2,
    ) -> None:
        self._agent = agent
        self._client = client
        self._project_root = project_root
        self._timeout_seconds = timeout_seconds
        self._in_flight = threading.BoundedSemaphore(max(1, max_in_flight))

    def __call__(
        self,
        defect: Defect,
        regions: Sequence[Region],
        sources: dict[str, str],
        previous: Sequence[SetAsideCandidate] = (),
    ) -> MutationDescriptor | None:
        offered = [region for region in regions if region.path in sources]
        prompt = _prompt(defect, offered, sources, previous)
        request = {
            "kind": "coding-agent edit",
            "agent": self._agent.name,
            "model": self._agent.model or f"{self._agent.name} default",
            "prompt": prompt,
            "timeout_seconds": self._timeout_seconds,
        }
        response = self._client.replay_or_run(
            request, lambda: self._run(prompt), AGENT_STAGE, label=defect.id
        )
        return descriptor_from_changes(response, offered, sources)

    def _run(self, prompt: str) -> dict[str, Any]:
        with self._in_flight, agent_copy(self._project_root) as root:
            before = _snapshot(root)
            run = self._agent.run(
                root,
                prompt,
                forbidden=self._project_root.resolve(),
                timeout_seconds=self._timeout_seconds,
            )
            changes = _changes(root, before, self._project_root)
        usage = {} if run.cost_usd is None else {"cost_usd": run.cost_usd}
        return {
            "response": {"finished": run.finished, "detail": run.detail, "changes": changes},
            "usage": usage,
        }


def _prompt(
    defect: Defect,
    regions: Sequence[Region],
    sources: dict[str, str],
    previous: Sequence[SetAsideCandidate],
) -> str:
    """The same defect fields and numbered regions the one-call builder is shown,
    under instructions for editing files rather than answering a schema."""
    parts = [_INSTRUCTIONS, _subject(defect, regions, sources)]
    if previous:
        parts.append(_earlier_candidates(previous))
    return "\n\n".join(parts)
