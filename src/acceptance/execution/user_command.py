"""The test command a user sets for a repository, and their agreement to its risk.

The review runs a project's tests to see whether they catch deliberately broken
code. By default it does that locked down, with the tool's own interpreter from
the repository root — which runs nothing for a project whose tests need their
own virtualenv, a subdirectory, or a database (#405).

So the user tells the tool, once per repository, the command they already run
their tests with. Nothing here works out a command, an interpreter or a
directory from the project's files: a command the user runs every day is known
to work, and every rule for guessing one is wrong for some repository.

**The command runs as on the user's machine**, with their environment and
network, against copies of their code that are broken on purpose. A planted
defect can do to a real database what the user's own runs never would. So the
command is saved only together with the user's explicit agreement, and the
agreement names exactly what was agreed to: a saved file whose command no
longer matches its agreement is refused rather than run.
`docs/DR-405-user-test-command.md` records the decision.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from acceptance.execution.sandbox import SandboxConfig
from acceptance.model_base import PersistableModel as _Model

__all__ = [
    "RISK_NOTICE",
    "SETTING_PATH",
    "SavedTestCommand",
    "TestCommandError",
    "agreement_for",
    "load_test_command",
    "sandbox_config",
    "save_test_command",
]

#: Where the setting lives, relative to the repository root. Inside the tool's
#: own local folder, which is never copied into a workspace and is not the
#: project's to commit: the agreement is one person's, about their machine.
SETTING_PATH = Path(".acceptance") / "test-command.json"

RISK_NOTICE = """\
Before saving this test command, please read what it will be used for.

`acceptance check` will run your tests with this command many times: once as
they are, and once for each of a number of copies of your code that have been
broken on purpose, to see whether your tests notice.

They will run the way they run on your machine: with all of your environment
variables (a DATABASE_URL, API keys) and with network access. A copy of your
code that is broken on purpose can do things your own test runs never would,
such as deleting every row of a table instead of one, or calling an outside
service many times.

Only agree if every database and service your tests can reach is safe to
damage, such as a throwaway test database. The tool does not check this.
"""


class TestCommandError(Exception):
    """The setting exists but cannot be used, with a message saying what to do."""

    # Not a pytest test class, whatever its name says.
    __test__ = False


class SavedTestCommand(_Model):
    """What the setting file holds."""

    command: str
    parallel_runs: int = 1
    #: `agreement_for(command, parallel_runs)` at the moment the user said yes.
    agreed_to: str


def agreement_for(command: str, parallel_runs: int) -> str:
    """A fingerprint of exactly what the user agreed to run.

    Both values are in it: agreeing to one run at a time is not agreeing to
    eight against the same database.
    """
    text = json.dumps({"command": command, "parallel_runs": parallel_runs}, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def save_test_command(repo: Path, command: str, parallel_runs: int) -> Path:
    """Write the setting with the user's agreement. Call only after they said yes."""
    # Validated through the sandbox's own rules, so a value the run would
    # refuse is refused here, at the moment the user can still fix it.
    SandboxConfig(test_command=command, parallel_runs=parallel_runs)
    saved = SavedTestCommand(
        command=command,
        parallel_runs=parallel_runs,
        agreed_to=agreement_for(command, parallel_runs),
    )
    path = repo / SETTING_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(saved.model_dump(), indent=2, sort_keys=True) + "\n")
    return path


def load_test_command(repo: Path) -> SavedTestCommand | None:
    """The saved setting, `None` when there is none.

    Raises `TestCommandError` when the file is unreadable, or when its command
    or parallel count is not the one the user agreed to — the file was edited
    by hand. That is refused, not run: the agreement is the only safeguard, and
    a command nobody agreed to is exactly what it exists to stop.
    """
    path = repo / SETTING_PATH
    if not path.is_file():
        return None
    try:
        saved = SavedTestCommand.model_validate(json.loads(path.read_text()))
    except (OSError, ValueError, ValidationError) as error:
        raise TestCommandError(
            f"{path} cannot be read ({error}). Set the test command again with\n"
            '  acceptance set-test-command "<the command you run your tests with>"'
        ) from error
    if saved.agreed_to != agreement_for(saved.command, saved.parallel_runs):
        raise TestCommandError(
            f"the test command in {path} has changed since it was agreed to, so it "
            "will not be run. Set it again, and agree to it, with\n"
            f"  acceptance set-test-command {_quoted(saved.command)}"
        )
    return saved


def sandbox_config(saved: SavedTestCommand | None) -> SandboxConfig:
    """The run configuration for a repository's setting, or the locked-down default."""
    if saved is None:
        return SandboxConfig()
    return SandboxConfig(test_command=saved.command, parallel_runs=saved.parallel_runs)


def _quoted(command: str) -> str:
    return json.dumps(command)
