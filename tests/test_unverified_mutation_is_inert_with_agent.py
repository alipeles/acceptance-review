"""`test_unverified_mutation_is_inert.py`'s whole-review cases, with the edit
written by the coding agent (#338).

The guard file is not edited. Its class is run again here with three things
swapped in its module for the length of each test: every execution setting it
builds names a fake agent, the one-call builder's answer changes nothing so
every one-call candidate is set aside, and the fake agent writes the edit the
guard's own fixture describes. Each case therefore reaches the agent, and the
guard's assertions — the criterion is rated as if nothing ran, no verdict claims
the executed tier, the judge is told nothing of the edit, the report marks the
result not counted — are asserted about an agent-written edit.

`test_the_edit_came_from_the_agent` is the control: without it, every inherited
case would pass just as well if the agent had never been reached.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tests.test_unverified_mutation_is_inert as guard
from acceptance.mutation.agent import AGENTS, AgentRun, AgentSettings
from acceptance.mutation.settings import ExecutionSettings
from tests.test_unverified_mutation_is_inert import (
    TestThroughTheWholeReview as _GuardedReview,
)
from tests.test_unverified_mutation_is_inert import repo  # noqa: F401 — a fixture

#: The guard fixture's injected edit, written by the agent instead.
_EDIT = guard._JUDGMENTS["_Descriptor"]["replacement"]
_LINE = guard._JUDGMENTS["_Descriptor"]["start_line"]


class _WritesTheGuardEdit:
    name = "fake"
    model = None

    def __init__(self, runs: list[Path]) -> None:
        self._runs = runs

    def run(self, workdir, prompt, *, forbidden, timeout_seconds):
        self._runs.append(workdir)
        target = workdir / "loan.py"
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        lines[_LINE - 1] = _EDIT
        target.write_text("".join(lines), encoding="utf-8")
        return AgentRun(finished=True, cost_usd=0.0, detail="fake")


@pytest.fixture(autouse=True)
def the_agent_writes_every_edit(monkeypatch):
    runs: list[Path] = []
    monkeypatch.setitem(AGENTS, "fake", lambda model, executable: _WritesTheGuardEdit(runs))

    def with_agent(**fields):
        return ExecutionSettings(**fields, agent=AgentSettings(agent="fake"))

    unchanged = guard._HEAD.splitlines(keepends=True)[_LINE - 1]
    judgments = {
        **guard._JUDGMENTS,
        "_Descriptor": {**guard._JUDGMENTS["_Descriptor"], "replacement": unchanged},
    }
    monkeypatch.setattr(guard, "ExecutionSettings", with_agent)
    # Read from the module at call time by `_review` and by the verified-result
    # case, so patching the global reaches both.
    monkeypatch.setattr(guard, "_JUDGMENTS", judgments)
    return runs


class TestThroughTheWholeReviewWithTheAgent(_GuardedReview):
    def test_the_edit_came_from_the_agent(self, repo, the_agent_writes_every_edit):  # noqa: F811
        review = guard._review(repo, execution=guard.ExecutionSettings(verify_edits=True))
        (attempt,) = review.mutation_attempts
        assert len(the_agent_writes_every_edit) == 1
        assert attempt.candidate_used == attempt.candidates_asked
        assert attempt.candidates_asked > 1
        assert attempt.descriptor.replacement == _EDIT
        assert attempt.observed is True
        assert attempt.verified is False
