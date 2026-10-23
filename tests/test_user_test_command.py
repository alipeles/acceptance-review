"""Running a project's tests the way the user runs them (#405).

Like `test_execution_sandbox.py`, these spawn real pytest processes against
throwaway projects: which interpreter ran, which directory pytest took as its
root, what environment a test saw and whether two runs overlapped are
properties of processes, and a mocked subprocess would show none of them.

The project these tests build is the shape #405 reported: the Python project in
`api/`, with its own pytest configuration and its own interpreter, and nothing
at the repository root.
"""

import os
import shlex
import socket
import sys
import textwrap
import threading
from pathlib import Path

import pytest

from acceptance import cli
from acceptance.execution.outcome import TestOutcomeKind
from acceptance.execution.sandbox import (
    WORKER_VAR,
    SandboxConfig,
    collect_tests,
    passed_environment_names,
    run_tests,
)
from acceptance.execution.user_command import (
    RISK_NOTICE,
    SETTING_PATH,
    TestCommandError,
    load_test_command,
    save_test_command,
)
from acceptance.mutation.baseline import establish_baseline
from acceptance.mutation.workspace import copied_project

pytestmark = pytest.mark.skipif(
    os.name != "posix", reason="the sandbox's process-group control is POSIX-only"
)

#: The command #405's user runs: change into the project, use its interpreter.
COMMAND = "cd api && .venv/bin/python -m pytest"
TEST_ID = "api/tests/test_service.py::test_uses_the_project"


def _subdirectory_project(tmp_path: Path, test_body: str) -> Path:
    """A repository whose Python project lives in `api/`, as in #405.

    `api/.venv/bin/python` stands in for the project's own virtualenv: it marks
    the environment, so a test can tell which interpreter ran it, then hands
    over to this interpreter. `projdep` is a dependency only `api/`'s own pytest
    configuration puts on the path.
    """
    root = tmp_path / "repo"
    api = root / "api"
    (api / "tests").mkdir(parents=True)
    (api / "vendor").mkdir()
    (api / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["vendor"]\ntestpaths = ["tests"]\n'
    )
    (api / "vendor" / "projdep.py").write_text("VALUE = 42\n")
    (api / "tests" / "test_service.py").write_text(textwrap.dedent(test_body))
    interpreter = api / ".venv" / "bin" / "python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        f'#!/bin/sh\nexport PROJECT_INTERPRETER=1\nexec {shlex.quote(sys.executable)} "$@"\n'
    )
    interpreter.chmod(0o755)
    return root


def _command(**overrides) -> SandboxConfig:
    values = {"test_command": COMMAND, "per_test_seconds": 20.0}
    values.update(overrides)
    return SandboxConfig(**values)


_USES_THE_PROJECT = """
    import os

    import projdep


    def test_uses_the_project():
        assert projdep.VALUE == 42
        assert os.environ.get("PROJECT_INTERPRETER") == "1"
"""


# --- the main fix: a project in a subdirectory has its tests run -------------


def test_a_subdirectory_project_s_tests_are_collected_under_the_repository_s_names(tmp_path):
    """pytest takes `api/` as its root and names the test `tests/test_service.py::…`.
    The review asks for `api/tests/…`. Before #405 nothing matched, so every
    test was set aside as one pytest "declines" — even with the right interpreter."""
    root = _subdirectory_project(tmp_path, _USES_THE_PROJECT)

    assert collect_tests([TEST_ID], root, _command()) == {TEST_ID}


def test_the_names_match_without_a_test_command_too(tmp_path):
    """The renaming is in the plugin, so the locked-down run gets it as well."""
    root = _subdirectory_project(tmp_path, "def test_uses_the_project():\n    assert True\n")
    locked = SandboxConfig(interpreter=sys.executable, per_test_seconds=10.0)

    assert collect_tests([TEST_ID], root, locked) == {TEST_ID}
    assert run_tests([TEST_ID], root, locked).outcome_for(TEST_ID).kind is TestOutcomeKind.PASSED


def test_the_user_s_command_runs_the_tests_with_the_project_s_own_interpreter(tmp_path):
    root = _subdirectory_project(tmp_path, _USES_THE_PROJECT)

    outcome = run_tests([TEST_ID], root, _command()).outcome_for(TEST_ID)

    assert outcome.kind is TestOutcomeKind.PASSED, outcome


def test_without_the_command_the_same_test_does_not_get_the_project_s_interpreter(tmp_path):
    """The contrast that makes the test above evidence: the locked-down run uses
    the tool's own interpreter, so the project's marker is absent and the test
    fails. If the command were ignored, both tests would agree."""
    root = _subdirectory_project(tmp_path, _USES_THE_PROJECT)
    locked = SandboxConfig(interpreter=sys.executable, per_test_seconds=10.0)

    assert run_tests([TEST_ID], root, locked).outcome_for(TEST_ID).kind is TestOutcomeKind.FAILED


# --- as on the user's machine: their environment and the network ----------


def test_the_user_s_environment_reaches_the_tests(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://tester@localhost/throwaway")
    root = _subdirectory_project(
        tmp_path,
        """
        import os

        def test_uses_the_project():
            assert os.environ["DATABASE_URL"] == "postgresql://tester@localhost/throwaway"
        """,
    )

    outcome = run_tests([TEST_ID], root, _command()).outcome_for(TEST_ID)

    assert outcome.kind is TestOutcomeKind.PASSED, outcome


def test_the_network_is_not_blocked_under_a_test_command(tmp_path):
    """Checked by what the plugin installs rather than by opening a connection,
    which the machine running this suite may itself forbid. The locked-down
    tests in `test_execution_sandbox.py` show the same probe sees the block."""
    root = _subdirectory_project(
        tmp_path,
        """
        import socket

        def test_uses_the_project():
            assert "install_network_block" not in socket.create_connection.__qualname__
            assert "install_network_block" not in socket.socket.connect.__qualname__
        """,
    )

    outcome = run_tests([TEST_ID], root, _command()).outcome_for(TEST_ID)

    assert outcome.kind is TestOutcomeKind.PASSED, outcome
    # And this process, which loaded no plugin, is untouched either way.
    assert "install_network_block" not in socket.create_connection.__qualname__


def test_the_network_is_still_blocked_without_a_test_command(tmp_path):
    root = _subdirectory_project(
        tmp_path,
        """
        import socket

        def test_uses_the_project():
            assert "install_network_block" in socket.create_connection.__qualname__
        """,
    )
    locked = SandboxConfig(interpreter=sys.executable, per_test_seconds=10.0)

    assert run_tests([TEST_ID], root, locked).outcome_for(TEST_ID).kind is TestOutcomeKind.PASSED


# --- copies of the project, which is where broken code is run -------------


def test_the_command_works_in_a_copy_and_the_original_virtualenv_survives(tmp_path):
    """A copy leaves `.venv` out, so `.venv/bin/python` did not exist in it and
    every test would pass in the project but fail in the unmodified copy."""
    root = _subdirectory_project(tmp_path, _USES_THE_PROJECT)
    interpreter = root / "api" / ".venv" / "bin" / "python"

    with copied_project(root, "acceptance-test-") as copy:
        assert (copy / "api" / ".venv").is_symlink()
        outcome = run_tests([TEST_ID], copy, _command()).outcome_for(TEST_ID)

    assert outcome.kind is TestOutcomeKind.PASSED, outcome
    assert interpreter.is_file()


def test_a_copy_for_a_coding_agent_gets_no_link_to_the_virtualenv(tmp_path):
    root = _subdirectory_project(tmp_path, _USES_THE_PROJECT)

    with copied_project(root, "acceptance-test-", link_environments=False) as copy:
        assert not (copy / "api" / ".venv").exists()


# --- how many runs at once ----------------------------------------------------


_LOGS_ITS_RUN = """
    import os
    import time

    def test_uses_the_project():
        log = os.environ["RUN_LOG"]
        with open(log, "a") as handle:
            handle.write(f"start {os.environ['ACCEPTANCE_WORKER']} {time.time()}\\n")
        time.sleep(0.5)
        with open(log, "a") as handle:
            handle.write(f"end {os.environ['ACCEPTANCE_WORKER']} {time.time()}\\n")
"""


def _run_together(root: Path, config: SandboxConfig, count: int) -> list:
    results: list = [None] * count

    def one(index: int) -> None:
        results[index] = run_tests([TEST_ID], root, config).outcome_for(TEST_ID)

    threads = [threading.Thread(target=one, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def test_by_default_no_two_runs_of_the_command_overlap(tmp_path, monkeypatch):
    log = tmp_path / "runs.log"
    monkeypatch.setenv("RUN_LOG", str(log))
    root = _subdirectory_project(tmp_path, _LOGS_ITS_RUN)

    outcomes = _run_together(root, _command(), 3)

    assert all(o.kind is TestOutcomeKind.PASSED for o in outcomes), outcomes
    events = [line.split() for line in log.read_text().splitlines()]
    # Serial means the log alternates start, end, start, end — never two starts
    # in a row — and every run was told it is run 1.
    assert [kind for kind, _, _ in events] == ["start", "end"] * 3
    assert {worker for _, worker, _ in events} == {"1"}


def test_with_two_allowed_two_runs_happen_at_once_and_each_knows_its_number(tmp_path, monkeypatch):
    """Each run waits until the other has started. Run one at a time, the first
    would wait for nothing and fail; both passing is the evidence that they
    were in flight together."""
    started = tmp_path / "started"
    started.mkdir()
    monkeypatch.setenv("STARTED_DIR", str(started))
    root = _subdirectory_project(
        tmp_path,
        """
        import os
        import time
        from pathlib import Path

        def test_uses_the_project():
            here = Path(os.environ["STARTED_DIR"])
            (here / os.environ["ACCEPTANCE_WORKER"]).touch()
            deadline = time.time() + 15
            while len(list(here.iterdir())) < 2:
                assert time.time() < deadline, "the other run never started"
                time.sleep(0.05)
        """,
    )

    outcomes = _run_together(root, _command(parallel_runs=2), 2)

    assert all(o.kind is TestOutcomeKind.PASSED for o in outcomes), outcomes
    assert sorted(p.name for p in started.iterdir()) == ["1", "2"]


def test_a_locked_down_run_is_not_told_a_worker_number(tmp_path):
    root = _subdirectory_project(
        tmp_path,
        f"""
        import os

        def test_uses_the_project():
            assert "{WORKER_VAR}" not in os.environ
        """,
    )
    locked = SandboxConfig(interpreter=sys.executable, per_test_seconds=10.0)

    assert run_tests([TEST_ID], root, locked).outcome_for(TEST_ID).kind is TestOutcomeKind.PASSED


# --- when no command is set and nothing can be run ---------------------------


def test_with_no_command_and_nothing_collected_the_reason_says_to_set_one(tmp_path):
    root = _subdirectory_project(tmp_path, _USES_THE_PROJECT)
    (root / "api" / "vendor" / "projdep.py").unlink()  # the import now fails

    baseline = establish_baseline(
        [TEST_ID], root, SandboxConfig(interpreter=sys.executable, per_test_seconds=10.0)
    )

    [set_aside] = baseline.set_aside
    assert "acceptance set-test-command" in set_aside.reason
    assert "declines" not in set_aside.reason


def test_with_a_command_set_a_test_pytest_refuses_is_still_one_it_declines(tmp_path):
    root = _subdirectory_project(tmp_path, _USES_THE_PROJECT)
    (root / "api" / "vendor" / "projdep.py").unlink()

    [set_aside] = establish_baseline([TEST_ID], root, _command()).set_aside

    assert "declines" in set_aside.reason
    assert "set-test-command" not in set_aside.reason


# --- setting the command, and agreeing to the risk ---------------------------


def _answers(*replies: str):
    asked: list[str] = []

    def ask(prompt: str) -> str:
        asked.append(prompt)
        return replies[len(asked) - 1]

    ask.asked = asked  # type: ignore[attr-defined]
    return ask


def test_setting_the_command_shows_the_risk_and_saves_only_on_yes(tmp_path, capsys):
    ask = _answers("yes")

    code = cli.run_set_test_command(tmp_path, COMMAND, 1, interactive=True, ask=ask)

    assert code == 0
    out = capsys.readouterr().out
    assert RISK_NOTICE in out
    assert COMMAND in out
    saved = load_test_command(tmp_path)
    assert (saved.command, saved.parallel_runs) == (COMMAND, 1)


@pytest.mark.parametrize("reply", ["no", "", "y", "sure"])
def test_anything_but_yes_saves_nothing(tmp_path, reply):
    code = cli.run_set_test_command(tmp_path, COMMAND, 1, interactive=True, ask=_answers(reply))

    assert code == 1
    assert not (tmp_path / SETTING_PATH).exists()


def test_off_a_terminal_nothing_is_asked_and_nothing_is_saved(tmp_path, capsys):
    """An agent runs commands without a terminal and cannot agree for the user."""
    ask = _answers("yes")

    code = cli.run_set_test_command(tmp_path, COMMAND, 1, interactive=False, ask=ask)

    assert code == 1
    assert ask.asked == []
    assert not (tmp_path / SETTING_PATH).exists()
    assert "in a terminal" in capsys.readouterr().err


def test_changing_the_command_asks_again_and_names_what_it_replaces(tmp_path, capsys):
    save_test_command(tmp_path, COMMAND, 1)
    capsys.readouterr()
    ask = _answers("no")

    code = cli.run_set_test_command(tmp_path, "uv run pytest", 1, interactive=True, ask=ask)

    assert code == 1
    assert len(ask.asked) == 1
    assert f"This replaces: {COMMAND}" in capsys.readouterr().out
    assert load_test_command(tmp_path).command == COMMAND  # the old one stands


def test_a_command_edited_by_hand_is_refused_rather_than_run(tmp_path):
    path = save_test_command(tmp_path, COMMAND, 1)
    path.write_text(path.read_text().replace("cd api", "cd elsewhere"))

    with pytest.raises(TestCommandError, match="has changed since it was agreed to"):
        load_test_command(tmp_path)


def test_raising_the_parallel_count_by_hand_is_refused_too(tmp_path):
    path = save_test_command(tmp_path, COMMAND, 1)
    path.write_text(path.read_text().replace('"parallel_runs": 1', '"parallel_runs": 8'))

    with pytest.raises(TestCommandError):
        load_test_command(tmp_path)


# --- what `check` does with it -------------------------------------------------


@pytest.fixture
def captured_check(monkeypatch, tmp_path):
    """`main(["check", …])` up to the point it hands over to `run_check`."""
    monkeypatch.chdir(tmp_path)
    seen: dict = {}

    def fake_run_check(*args, **kwargs):
        seen["execution"] = kwargs["execution"]
        raise cli.CliError("stopped by the test")

    monkeypatch.setattr(cli, "run_check", fake_run_check)
    return seen


def test_check_runs_with_the_saved_command_and_prints_it(
    tmp_path, captured_check, capsys, monkeypatch
):
    monkeypatch.setenv("DATABASE_URL", "postgresql://tester:s3cret-pw@localhost/db")
    save_test_command(tmp_path, COMMAND, 2)

    cli.main(["check", "--task", "t.md", "--base", "HEAD"])

    sandbox = captured_check["execution"].sandbox
    assert (sandbox.test_command, sandbox.parallel_runs) == (COMMAND, 2)
    err = capsys.readouterr().err
    assert f"tests run with: {COMMAND}" in err
    assert "DATABASE_URL" in err
    assert "s3cret-pw" not in err


def test_check_with_no_command_runs_locked_down_and_says_so(tmp_path, captured_check, capsys):
    cli.main(["check", "--task", "t.md", "--base", "HEAD"])

    assert captured_check["execution"].sandbox.test_command is None
    assert "locked down" in capsys.readouterr().err


def test_check_refuses_a_command_nobody_agreed_to(tmp_path, captured_check, capsys):
    path = save_test_command(tmp_path, COMMAND, 1)
    path.write_text(path.read_text().replace("cd api", "cd elsewhere"))

    assert cli.main(["check", "--task", "t.md", "--base", "HEAD"]) == 1
    assert "execution" not in captured_check
    assert "has changed since it was agreed to" in capsys.readouterr().err


def test_the_names_listed_are_the_user_s_whole_environment_under_a_command(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "x")

    assert "DATABASE_URL" in passed_environment_names(_command())
    assert "DATABASE_URL" not in passed_environment_names(SandboxConfig())
