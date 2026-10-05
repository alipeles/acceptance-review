"""The coding-agent edit builder (#338): confined, routed last, and given no
privileged path.

Every test here drives a fake agent: a class with the `CodingAgent` interface
that edits files in the directory it is handed, the way a real agent would. The
real sandbox runs the tests against its edits, so the checks it meets are the
real ones. Whether Claude Code itself honours its confinement flags is checked
once, live, and recorded in `docs/DR-338-agent-edit-builder.md`; what is pinned
here is that the flags are the ones that decision names.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from acceptance.llm import Mode, ModelClient, TranscriptNotFoundError, TranscriptStore
from acceptance.mutation.agent import (
    AGENT_STAGE,
    AGENTS,
    AgentDescriptorBuilder,
    AgentRun,
    AgentSettings,
    ClaudeCodeAgent,
    _claude_outcome,
    agent_copy,
    descriptor_from_changes,
)
from acceptance.mutation.attempt import CandidateCause, MutationDescriptor, MutationOutcomeKind
from acceptance.mutation.baseline import establish_baseline
from acceptance.mutation.descriptor import STAGE as DESCRIPTOR_STAGE
from acceptance.mutation.region import Region
from acceptance.mutation.runner import DEFAULT_MAX_CANDIDATES, run_mutations
from acceptance.mutation.settings import ExecutionSettings
from acceptance.review_state import ChangeSet, Defect, DefectSet, DefectType, DiffHunk, FileChange
from acceptance.usage import per_label, render_per_label

LOAN = '''def amortize(principal, months):
    """Equal monthly payments."""
    payment = principal / months
    return [payment for _ in range(months)]
'''

TEST_LOAN = """from loan import amortize


def test_returns_a_payment_for_each_month():
    schedule = amortize(1200.0, 12)
    assert len(schedule) == 12
"""

TEST_ID = "test_loan.py::test_returns_a_payment_for_each_month"
ONE_SHORT = "    return [payment for _ in range(months - 1)]\n"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "tests").mkdir(parents=True)
    (root / ".claude").mkdir()
    (root / "loan.py").write_text(LOAN, encoding="utf-8")
    (root / "test_loan.py").write_text(TEST_LOAN, encoding="utf-8")
    (root / "tests" / "test_more.py").write_text("def test_x():\n    pass\n", encoding="utf-8")
    (root / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    return root


@pytest.fixture
def change_set() -> ChangeSet:
    return ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="loan.py",
                status="added",
                category="source",
                hunks=[
                    DiffHunk(
                        header="@@ -0,0 +1,4 @@",
                        old_start=0,
                        old_lines=0,
                        new_start=1,
                        new_lines=4,
                        content=LOAN,
                    )
                ],
            )
        ],
    )


DEFECT = Defect(
    id="d-one-short",
    obligation_id="o1",
    type=DefectType.OTHER,
    description="one payment too few",
    expected_behavior="one payment per month",
    defective_behavior="one payment fewer than the months",
    code_refs=["loan.py#0"],
)
REGION = Region(label="loan.py#0", path="loan.py", start_line=1, end_line=4)


def _client(mode: Mode = Mode.RECORD, store: TranscriptStore | None = None) -> ModelClient:
    return ModelClient(
        model="test-model", mode=mode, store=store or TranscriptStore(tempfile.mkdtemp())
    )


class FakeAgent:
    """Edits the directory it is handed with `edit`, and notes what it saw."""

    name = "fake"
    model = None

    def __init__(self, edit=None, *, finished: bool = True, cost: float | None = 0.25):
        self._edit = edit
        self._finished = finished
        self._cost = cost
        self.runs: list[dict] = []

    def run(self, workdir, prompt, *, forbidden, timeout_seconds):
        self.runs.append(
            {
                "files": sorted(
                    p.relative_to(workdir).as_posix() for p in workdir.rglob("*") if p.is_file()
                ),
                "dirs": sorted(
                    p.relative_to(workdir).as_posix() for p in workdir.rglob("*") if p.is_dir()
                ),
                "prompt": prompt,
                "forbidden": forbidden,
                "workdir": workdir,
            }
        )
        if self._edit is not None:
            self._edit(workdir)
        return AgentRun(finished=self._finished, cost_usd=self._cost, detail="fake")


def _replace_line(number: int, text: str):
    def edit(workdir: Path) -> None:
        target = workdir / "loan.py"
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        lines[number - 1] = text
        target.write_text("".join(lines), encoding="utf-8")

    return edit


def _never(_defect, _regions, _sources, _previous=()):
    """A one-call builder whose every candidate changes nothing, so each is set
    aside and the runner reaches the fallback."""
    return MutationDescriptor(
        path="loan.py",
        start_line=3,
        end_line=3,
        replacement="    payment = principal / months\n",
        region_label="loan.py#0",
    )


def _sets() -> list[DefectSet]:
    return [DefectSet(obligation_id="o1", defects=[DEFECT])]


class TestTheAgentCannotSeeTheTests:
    def test_its_copy_has_no_test_files_and_no_agent_configuration(self, project):
        agent = FakeAgent()
        AgentDescriptorBuilder(agent, _client(), project)(DEFECT, [REGION], {"loan.py": LOAN})
        (run,) = agent.runs
        assert run["files"] == ["loan.py"]
        assert "tests" not in run["dirs"], "an emptied tests directory still says where they were"
        assert ".claude" not in run["dirs"]
        # The original is untouched: the deletion happened in a copy.
        assert (project / "test_loan.py").is_file()
        assert (project / "tests" / "test_more.py").is_file()

    def test_it_works_in_a_copy_and_is_told_the_original_is_forbidden(self, project):
        agent = FakeAgent()
        AgentDescriptorBuilder(agent, _client(), project)(DEFECT, [REGION], {"loan.py": LOAN})
        (run,) = agent.runs
        assert run["forbidden"] == project.resolve()
        assert project.resolve() not in run["workdir"].resolve().parents
        assert str(project.resolve()) not in run["prompt"], "the prompt names the original"

    def test_the_copy_uses_the_same_test_definition_as_the_one_call_builder(self, project):
        (project / "pkg").mkdir()
        (project / "pkg" / "thing_test.py").write_text("x = 1\n", encoding="utf-8")
        (project / "pkg" / "thing.py").write_text("x = 1\n", encoding="utf-8")
        with agent_copy(project) as root:
            assert (root / "pkg" / "thing.py").is_file()
            assert not (root / "pkg" / "thing_test.py").exists()


class TestClaudeCodeIsConfinedByItsOwnFlags:
    """The decision's three settings, each pinned. Removing any one would leave
    the copy as the only barrier, and the original is still on disk."""

    def _command(self, forbidden: Path) -> list[str]:
        return ClaudeCodeAgent(model="claude-sonnet-5-5").command(forbidden)

    def _flag(self, command: list[str], name: str) -> str:
        return command[command.index(name) + 1]

    def test_no_shell_is_available(self, tmp_path):
        tools = self._flag(self._command(tmp_path), "--tools").split(",")
        assert "Bash" not in tools
        assert set(tools) == {"Read", "Edit", "Glob", "Grep"}

    def test_reads_and_edits_of_the_original_are_denied(self, tmp_path):
        settings = json.loads(self._flag(self._command(tmp_path), "--settings"))
        rule = f"/{tmp_path.resolve()}/**"
        assert f"Read({rule})" in settings["permissions"]["deny"]
        assert f"Edit({rule})" in settings["permissions"]["deny"]
        assert settings["permissions"]["allow"] == ["Read(./**)", "Edit(./**)"]

    def test_anything_not_allowed_is_refused_rather_than_awaiting_approval(self, tmp_path):
        assert self._flag(self._command(tmp_path), "--permission-mode") == "dontAsk"

    def test_the_prompt_goes_on_stdin_not_the_command_line(self, tmp_path):
        command = self._command(tmp_path)
        assert command[:2] == ["claude", "-p"]
        assert self._flag(command, "--model") == "claude-sonnet-5-5"

    def test_its_result_object_gives_the_cost(self):
        run = _claude_outcome(0, json.dumps({"total_cost_usd": 0.42, "is_error": False}), "")
        assert run == AgentRun(finished=True, cost_usd=0.42, detail="finished")

    def test_an_error_result_is_not_finished(self):
        run = _claude_outcome(1, json.dumps({"total_cost_usd": 0.1, "is_error": True}), "boom")
        assert run.finished is False
        assert run.cost_usd == 0.1


class TestRoutedLast:
    def test_the_agent_is_asked_only_after_every_one_call_candidate_was_set_aside(
        self, project, change_set
    ):
        baseline = establish_baseline([TEST_ID], project)
        agent = FakeAgent(_replace_line(4, ONE_SHORT))
        (attempt,) = run_mutations(
            _sets(),
            change_set,
            project,
            baseline,
            _never,
            fallback=AgentDescriptorBuilder(agent, _client(), project),
        )
        assert len(agent.runs) == 1
        assert attempt.outcome is MutationOutcomeKind.KILLED
        assert attempt.candidates_asked == DEFAULT_MAX_CANDIDATES + 1
        assert attempt.candidate_used == DEFAULT_MAX_CANDIDATES + 1
        assert [c.cause for c in attempt.set_aside_candidates] == (
            [CandidateCause.CHANGED_NOTHING] * DEFAULT_MAX_CANDIDATES
        )
        # It was shown the refused candidates, as a later one-call candidate is.
        assert "Earlier edits for this defect" in agent.runs[0]["prompt"]

    def test_the_agent_is_not_asked_when_a_one_call_candidate_is_used(self, project, change_set):
        baseline = establish_baseline([TEST_ID], project)
        agent = FakeAgent(_replace_line(4, ONE_SHORT))

        def works(_d, _r, _s, _p=()):
            return MutationDescriptor(
                path="loan.py",
                start_line=4,
                end_line=4,
                replacement=ONE_SHORT,
                region_label="loan.py#0",
            )

        (attempt,) = run_mutations(
            _sets(),
            change_set,
            project,
            baseline,
            works,
            fallback=AgentDescriptorBuilder(agent, _client(), project),
        )
        assert agent.runs == []
        assert attempt.candidate_used == 1

    def test_unconfigured_execution_settings_name_no_agent(self):
        assert ExecutionSettings().agent is None


class TestNoPrivilegedPath:
    """The agent's edit meets the checks every candidate meets, and failing one
    sets it aside exactly as it would a one-call candidate."""

    def _attempt(self, project, change_set, edit):
        baseline = establish_baseline([TEST_ID], project)
        (attempt,) = run_mutations(
            _sets(),
            change_set,
            project,
            baseline,
            _never,
            fallback=AgentDescriptorBuilder(FakeAgent(edit), _client(), project),
        )
        return attempt

    def test_an_edit_that_breaks_the_module_is_refused_after_the_run(self, project, change_set):
        attempt = self._attempt(
            project, change_set, _replace_line(4, "    return [nope for _ in range(months)]\n")
        )
        assert attempt.outcome is MutationOutcomeKind.NO_USABLE_EDIT
        assert attempt.set_aside_candidates[-1].cause is CandidateCause.REFUSED_AFTER_RUN

    def test_an_edit_that_changes_only_a_comment_fails_the_text_checks(self, project, change_set):
        attempt = self._attempt(
            project, change_set, _replace_line(3, "    payment = principal / months  # n\n")
        )
        assert attempt.outcome is MutationOutcomeKind.NO_USABLE_EDIT
        assert attempt.set_aside_candidates[-1].cause is CandidateCause.CHANGED_NOTHING

    def test_two_separate_edits_are_no_usable_answer(self, project, change_set):
        def two(workdir: Path) -> None:
            _replace_line(1, "def amortize(principal, months, x=0):\n")(workdir)
            _replace_line(4, ONE_SHORT)(workdir)

        attempt = self._attempt(project, change_set, two)
        assert attempt.set_aside_candidates[-1].cause is CandidateCause.UNUSABLE_ANSWER

    def test_an_edit_outside_the_named_region_is_refused_by_the_containment_check(self):
        region = Region(label="loan.py#0", path="loan.py", start_line=1, end_line=2)
        response = {
            "finished": True,
            "changes": [
                {
                    "path": "loan.py",
                    "deleted": False,
                    "hunks": [{"start_line": 4, "end_line": 4, "replacement": ONE_SHORT}],
                }
            ],
        }
        descriptor = descriptor_from_changes(response, [region], {"loan.py": LOAN})
        # Handed on as one span, so the runner's containment check refuses it on
        # the record rather than this builder dropping it unseen.
        assert descriptor is not None and descriptor.start_line == 4


class TestWhatIsNoUsableAnswer:
    def _answer(self, project, agent):
        return AgentDescriptorBuilder(agent, _client(), project)(
            DEFECT, [REGION], {"loan.py": LOAN}
        )

    def test_a_run_that_did_not_finish(self, project):
        agent = FakeAgent(_replace_line(4, ONE_SHORT), finished=False)
        assert self._answer(project, agent) is None

    def test_a_run_that_changed_nothing(self, project):
        assert self._answer(project, FakeAgent()) is None

    def test_a_new_file(self, project):
        def create(workdir: Path) -> None:
            (workdir / "extra.py").write_text("x = 1\n", encoding="utf-8")

        assert self._answer(project, FakeAgent(create)) is None

    def test_an_edit_to_a_file_the_defect_did_not_name(self, project):
        (project / "other.py").write_text("x = 1\n", encoding="utf-8")

        def edit(workdir: Path) -> None:
            (workdir / "other.py").write_text("x = 2\n", encoding="utf-8")

        assert self._answer(project, FakeAgent(edit)) is None

    def test_one_span_is_returned_with_the_original_lines(self, project):
        descriptor = self._answer(project, FakeAgent(_replace_line(4, ONE_SHORT)))
        assert descriptor == MutationDescriptor(
            path="loan.py",
            start_line=4,
            end_line=4,
            replacement=ONE_SHORT,
            region_label="loan.py#0",
            original="    return [payment for _ in range(months)]\n",
        )

    def test_a_pure_insertion_takes_the_line_before_it(self):
        response = {
            "finished": True,
            "changes": [
                {
                    "path": "loan.py",
                    "deleted": False,
                    "hunks": [{"start_line": 4, "end_line": 3, "replacement": "    months -= 1\n"}],
                }
            ],
        }
        descriptor = descriptor_from_changes(response, [REGION], {"loan.py": LOAN})
        assert descriptor.start_line == descriptor.end_line == 3
        assert descriptor.replacement == "    payment = principal / months\n    months -= 1\n"


class TestTheDiffIsWhatIsRecorded:
    def test_a_replay_applies_the_recorded_diff_without_starting_the_agent(self, project):
        store = TranscriptStore(tempfile.mkdtemp())
        recorded = AgentDescriptorBuilder(
            FakeAgent(_replace_line(4, ONE_SHORT)), _client(Mode.RECORD, store), project
        )(DEFECT, [REGION], {"loan.py": LOAN})

        class Unstartable(FakeAgent):
            def run(self, *args, **kwargs):
                raise AssertionError("a replay started the agent")

        replayed = AgentDescriptorBuilder(Unstartable(), _client(Mode.REPLAY, store), project)(
            DEFECT, [REGION], {"loan.py": LOAN}
        )
        assert replayed == recorded

    def test_the_record_holds_the_diff_and_no_transcript(self, project):
        store = TranscriptStore(tempfile.mkdtemp())
        AgentDescriptorBuilder(
            FakeAgent(_replace_line(4, ONE_SHORT)), _client(Mode.RECORD, store), project
        )(DEFECT, [REGION], {"loan.py": LOAN})
        (path,) = Path(store.root).glob("*.json")
        record = json.loads(path.read_text())
        assert set(record["response"]) == {"finished", "detail", "changes"}
        (change,) = record["response"]["changes"]
        assert "-    return [payment for _ in range(months)]" in change["diff"]
        assert "+" + ONE_SHORT.rstrip("\n") in change["diff"]

    def test_two_recordings_of_the_same_input_are_byte_identical(self, project):
        records = []
        for _ in range(2):
            store = TranscriptStore(tempfile.mkdtemp())
            AgentDescriptorBuilder(
                FakeAgent(_replace_line(4, ONE_SHORT)), _client(Mode.RECORD, store), project
            )(DEFECT, [REGION], {"loan.py": LOAN})
            (path,) = Path(store.root).glob("*.json")
            records.append((path.name, path.read_bytes()))
        assert records[0] == records[1]

    def test_replay_without_a_recording_stops_rather_than_running_live(self, project):
        builder = AgentDescriptorBuilder(FakeAgent(), _client(Mode.REPLAY), project)
        with pytest.raises(TranscriptNotFoundError):
            builder(DEFECT, [REGION], {"loan.py": LOAN})


class TestCostPerDefect:
    def test_an_agent_run_is_recorded_under_its_stage_and_defect(self, project):
        client = _client()
        AgentDescriptorBuilder(FakeAgent(cost=0.5), client, project)(
            DEFECT, [REGION], {"loan.py": LOAN}
        )
        (call,) = client.observed_calls
        assert call["stage"] == AGENT_STAGE
        assert call["label"] == DEFECT.id
        assert call["usage"] == {"cost_usd": 0.5}
        assert isinstance(call["seconds"], float)

    def test_a_label_does_not_change_the_request_key(self):
        """So labelling the one-call builder's calls by defect re-records none
        of them."""
        from tests.support import client_dispatching

        response = {
            "code_currently_does": "cannot_tell",
            "region_label": "",
            "start_line": 0,
            "end_line": 0,
            "replacement": "",
            "decline": "none",
            "reason": "x",
        }
        from acceptance.mutation.descriptor import _Descriptor

        client = client_dispatching({"_Descriptor": response})
        messages = [{"role": "user", "content": "hi"}]
        client.complete(messages, _Descriptor, stage=DESCRIPTOR_STAGE)
        client.complete(messages, _Descriptor, stage=DESCRIPTOR_STAGE, label="d1")
        first, second = client.observed_calls
        assert first["key"] == second["key"]
        assert "label" not in first and second["label"] == "d1"

    def test_the_table_sets_both_builders_side_by_side(self):
        calls = [
            {"stage": DESCRIPTOR_STAGE, "label": "d1", "served_from": "provider",
             "usage": {"cost_usd": 0.01}, "seconds": 2.0},
            {"stage": DESCRIPTOR_STAGE, "label": "d1", "served_from": "provider",
             "usage": {"cost_usd": 0.02}, "seconds": 3.0},
            {"stage": AGENT_STAGE, "label": "d1", "served_from": "provider",
             "usage": {"cost_usd": 0.5}, "seconds": 60.0},
        ]  # fmt: skip
        rows = {
            (row.label, row.stage): row for row in per_label(calls, (DESCRIPTOR_STAGE, AGENT_STAGE))
        }
        assert rows[("d1", DESCRIPTOR_STAGE)].cost_usd == pytest.approx(0.03)
        assert rows[("d1", DESCRIPTOR_STAGE)].seconds == pytest.approx(5.0)
        assert rows[("d1", AGENT_STAGE)].cost_usd == pytest.approx(0.5)
        table = render_per_label(calls, (DESCRIPTOR_STAGE, AGENT_STAGE), only_with=AGENT_STAGE)
        assert "d1" in table and "$0.0300" in table and "$0.5000" in table

    def test_no_table_when_no_defect_reached_the_agent(self):
        calls = [{"stage": DESCRIPTOR_STAGE, "label": "d1", "served_from": "provider",
                  "usage": {"cost_usd": 0.01}, "seconds": 2.0}]  # fmt: skip
        assert render_per_label(calls, (DESCRIPTOR_STAGE, AGENT_STAGE), only_with=AGENT_STAGE) == ""


class TestAgentsAreAdapters:
    def test_claude_code_is_the_agent_available_today(self):
        assert sorted(AGENTS) == ["claude-code"]
        assert AgentSettings().agent == "claude-code"

    def test_an_unknown_agent_is_refused_at_configuration(self):
        with pytest.raises(ValueError, match="unknown coding agent"):
            AgentSettings(agent="codex")

    def test_a_new_agent_is_one_registry_entry(self, monkeypatch):
        monkeypatch.setitem(AGENTS, "fake", lambda model, executable: FakeAgent())
        assert AgentSettings(agent="fake").agent == "fake"
