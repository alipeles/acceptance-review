"""Runs a named set of tests in an isolated sandbox and reports what happened.

The contract every caller depends on: `run_tests` returns. It does not raise,
whatever the project, the interpreter or the clock does — a run that could not
happen is an ordinary result that leaves the review's conclusions where they
were, not an error to propagate. Nothing here elevates an evidence tier.

Three properties carry §17's execution-safety line, and each is enforced in the
only place it can be:

- **No network.** Installed inside the run by `netblock.py`, before the first
  test module is imported.
- **No credentials.** The subprocess environment is built from an allowlist
  rather than inherited, so nothing the launching machine holds is visible to
  the code under test.
- **A time budget.** Per test inside the run; for the run as a whole out here,
  as a wall-clock kill of the whole process group.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from pydantic import Field, field_validator

from acceptance.execution import netblock
from acceptance.execution.outcome import SandboxRunResult, TestOutcome, TestOutcomeKind
from acceptance.model_base import PersistableModel as _Model

__all__ = ["SandboxConfig", "run_tests"]

#: The module name the plugin is copied to and loaded under. Deliberately
#: unlikely to collide with anything in a project under review.
_PLUGIN_MODULE = "_acceptance_sandbox_netblock"

#: Environment variables the subprocess is allowed to inherit. Everything else
#: is dropped, which is what keeps the launching machine's credentials out of
#: the run. Nothing here can carry a secret: they are locale, paths and the
#: terminal.
_INHERITED_ENV = (
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "PATH",
    "SYSTEMROOT",
    "TMPDIR",
    "TZ",
    "USER",
)

#: How long the process group gets to die politely before it is killed.
_TERMINATION_GRACE_SECONDS = 5.0


class SandboxConfig(_Model):
    """Configuration for a sandboxed run, with conservative defaults.

    None of these is read from the project under review, and none is a measured
    value. `docs/DR-170-feasibility-probe.md` Decision 6 says why: this
    repository exhibits none of the four classes §8.3 names as infeasible, so it
    can supply counterexamples but not thresholds. The defaults are set to stop
    early rather than run long, and are calibrated at benchmarking against
    repositories that do exhibit those classes.

    The interpreter is likewise configuration with a conventional default — the
    one running the checker — and is never inferred from the project's files.
    """

    interpreter: str = Field(default_factory=lambda: sys.executable)
    per_test_seconds: float = 30.0
    total_seconds: float = 300.0

    @field_validator("per_test_seconds", "total_seconds")
    @classmethod
    def _budgets_are_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("a time budget must be greater than zero")
        return value

    @field_validator("interpreter")
    @classmethod
    def _interpreter_is_named(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("the interpreter must be named, not inferred")
        return value


def run_tests(
    test_ids: list[str],
    project_root: Path,
    config: SandboxConfig | None = None,
) -> SandboxRunResult:
    """Run exactly `test_ids` under the sandbox and report every one of them.

    Returns an outcome for each requested id, in the order requested. A test the
    run never reached is `not_started` with a reason, so that "tried and could
    not" stays distinguishable from "did not try".
    """
    config = config or SandboxConfig()
    requested = list(dict.fromkeys(test_ids))

    if not requested:
        # pytest with no node ids runs the entire suite. Refusing an empty
        # request is what makes "only the named tests are run" hold at the one
        # input where it would otherwise fail silently and expensively.
        return SandboxRunResult(outcomes=[])

    workspace = Path(tempfile.mkdtemp(prefix="acceptance-sandbox-"))
    try:
        return _run_in_workspace(requested, project_root, config, workspace)
    except Exception as error:  # noqa: BLE001 - the contract is that this returns
        return _all_not_started(requested, f"the sandbox could not run: {error}")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _run_in_workspace(
    requested: list[str],
    project_root: Path,
    config: SandboxConfig,
    workspace: Path,
) -> SandboxRunResult:
    report_path = workspace / "outcomes.jsonl"
    report_path.touch()
    plugin_dir = workspace / "plugin"
    plugin_dir.mkdir()
    shutil.copyfile(netblock.__file__, plugin_dir / f"{_PLUGIN_MODULE}.py")

    command = [
        config.interpreter,
        "-m",
        "pytest",
        "-p",
        _PLUGIN_MODULE,
        "-p",
        "no:cacheprovider",
        "--no-header",
        "-q",
        *requested,
    ]

    aborted, abort_reason = _spawn_and_wait(
        command,
        cwd=project_root,
        env=_sandbox_env(plugin_dir, report_path, config),
        total_seconds=config.total_seconds,
    )

    observed = _read_report(report_path)
    outcomes = [
        observed.get(test_id) or _not_started(test_id, abort_reason or _NOT_REACHED)
        for test_id in requested
    ]
    return SandboxRunResult(
        outcomes=outcomes,
        aborted=aborted,
        abort_reason=abort_reason,
    )


_NOT_REACHED = "the run ended before this test reported an outcome"


def _sandbox_env(plugin_dir: Path, report_path: Path, config: SandboxConfig) -> dict[str, str]:
    """Build the subprocess environment from an allowlist, never by inheriting.

    An allowlist rather than a denylist of credential-looking names: a denylist
    has to predict what a secret is called, and being wrong once is an
    execution-safety incident on someone else's repository.
    """
    env = {name: os.environ[name] for name in _INHERITED_ENV if name in os.environ}
    env["PYTHONPATH"] = str(plugin_dir)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env[netblock.REPORT_PATH_VAR] = str(report_path)
    env[netblock.PER_TEST_BUDGET_VAR] = repr(config.per_test_seconds)
    return env


def _spawn_and_wait(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    total_seconds: float,
) -> tuple[bool, str | None]:
    """Run the command under the whole-run budget. Returns (aborted, reason)."""
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        process.wait(timeout=total_seconds)
    except subprocess.TimeoutExpired:
        _terminate_group(process)
        return True, (
            f"the run exceeded its whole-run time budget of {total_seconds:g}s and was stopped"
        )
    return False, None


def _terminate_group(process: subprocess.Popen) -> None:
    """Stop the run without leaving anything executing behind it.

    The process group, not the process: pytest can spawn children, and killing
    only the one we hold a handle to would leave them running after the review
    has moved on. `start_new_session=True` at spawn is what makes the group ours
    to kill rather than our own.
    """
    for send in (_signal_group(signal.SIGTERM), _signal_group(signal.SIGKILL)):
        if process.poll() is not None:
            return
        send(process)
        deadline = time.monotonic() + _TERMINATION_GRACE_SECONDS
        while time.monotonic() < deadline:
            if process.poll() is not None:
                return
            time.sleep(0.05)


def _signal_group(number: int):
    def send(process: subprocess.Popen) -> None:
        try:
            os.killpg(os.getpgid(process.pid), number)
        except (ProcessLookupError, PermissionError):
            pass

    return send


def _read_report(report_path: Path) -> dict[str, TestOutcome]:
    """Read the outcomes the run wrote, ignoring anything malformed.

    A killed run can leave a half-written final line. Dropping it costs one
    `not_started` with a reason, which is honest; refusing to parse the file
    would lose every outcome the run did observe.
    """
    observed: dict[str, TestOutcome] = {}
    try:
        lines = report_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return observed

    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            outcome = TestOutcome(
                test_id=entry["test_id"],
                kind=TestOutcomeKind(entry["kind"]),
                reason=entry.get("reason"),
            )
        except Exception:  # noqa: BLE001, S112 - a torn line is expected here
            continue
        observed.setdefault(outcome.test_id, outcome)
    return observed


def _not_started(test_id: str, reason: str) -> TestOutcome:
    return TestOutcome(test_id=test_id, kind=TestOutcomeKind.NOT_STARTED, reason=reason)


def _all_not_started(test_ids: list[str], reason: str) -> SandboxRunResult:
    return SandboxRunResult(outcomes=[_not_started(test_id, reason) for test_id in test_ids])
