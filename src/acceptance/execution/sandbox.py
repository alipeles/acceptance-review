"""Runs a named set of tests and reports what happened.

The contract every caller depends on: `run_tests` returns. It does not raise,
whatever the project, the interpreter or the clock does — a run that could not
happen is an ordinary result that leaves the review's conclusions where they
were, not an error to propagate. Nothing here elevates an evidence tier.

There are two ways a run happens, and `SandboxConfig.test_command` picks one.

**No test command: locked down.** The tool's own interpreter runs pytest from
the project root, and three properties are enforced in the only place each can
be:

- **No network.** Installed inside the run by `netblock.py`, before the first
  test module is imported.
- **No credentials.** The subprocess environment is built from an allowlist
  rather than inherited, so nothing the launching machine holds is visible to
  the code under test.
- **A time budget.** Per test inside the run; for the run as a whole out here,
  as a wall-clock kill of the whole process group.

**A test command: as on the user's machine.** The command the user already runs
their tests with, which they set and agreed to (`execution/test_command.py`),
runs through the shell with the user's whole environment and network access.
Only the time budget still applies. The command is run exactly as given; this
module adds the plugin and the test names and nothing else, and guesses no
interpreter and no directory. `docs/DR-405-user-test-command.md` records why.

In both, the plugin reports every test by its path relative to the project
root, whatever directory pytest took as its own root, so the ids that come back
are the ids that were asked for.
"""

from __future__ import annotations

import json
import os
import queue
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import Field, field_validator

from acceptance.execution import netblock
from acceptance.execution.outcome import SandboxRunResult, TestOutcome, TestOutcomeKind
from acceptance.model_base import PersistableModel as _Model

__all__ = ["WORKER_VAR", "SandboxConfig", "collect_tests", "passed_environment_names", "run_tests"]

#: The module name the plugin is copied to and loaded under. Deliberately
#: unlikely to collide with anything in a project under review.
_PLUGIN_MODULE = "_acceptance_sandbox_netblock"

#: Under a test command, which of the `parallel_runs` slots a run holds, 1 to
#: N. A project whose tests share a service reads it to give each concurrent
#: run its own — a database named after it, say.
WORKER_VAR = "ACCEPTANCE_WORKER"

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

    `test_command`, when set, replaces the interpreter: it is the shell command
    the user runs their tests with, and the run is no longer locked down.
    `parallel_runs` is how many runs of that command may be in flight at once,
    which only the user can know — two runs sharing one database can corrupt
    each other's results. It means nothing without a test command, whose runs
    are hermetic and independent by construction.
    """

    interpreter: str = Field(default_factory=lambda: sys.executable)
    per_test_seconds: float = 30.0
    total_seconds: float = 300.0
    test_command: str | None = None
    parallel_runs: int = 1

    @field_validator("per_test_seconds", "total_seconds")
    @classmethod
    def _budgets_are_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("a time budget must be greater than zero")
        return value

    @field_validator("parallel_runs")
    @classmethod
    def _at_least_one_run(cls, value: int) -> int:
        if value < 1:
            raise ValueError("at least one run must be allowed at a time")
        return value

    @field_validator("test_command")
    @classmethod
    def _command_is_named(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("a test command must not be blank")
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


def collect_tests(
    test_ids: list[str],
    project_root: Path,
    config: SandboxConfig | None = None,
) -> set[str]:
    """Which of `test_ids` the project's own pytest can actually collect.

    Discovery finds test files by walking the repository. pytest decides what is
    a test by its own configuration, and the two disagree — a fixture directory
    the project excludes, a module whose imports only resolve somewhere else, a
    file with a syntax error, a `conftest.py` that excludes paths in Python code
    no config file would reveal.

    **A disagreement is not a small problem.** An id pytest cannot collect makes
    it exit with a usage error and run *nothing*, so one bad id costs the whole
    run. That is not hypothetical: it is what #45's own Gate 2 hit, where a
    single test belonging to an archetype fixture took all 341 candidate tests
    down with it and left the execution tier inert.

    So the candidate set becomes the intersection of what discovery found and
    what pytest will admit. The ids pytest omits are dropped by the caller with
    a recorded reason, never silently.

    Returns the collectable ids. On any failure — pytest missing, the project
    uninstallable, collection timing out — returns an **empty set**, which the
    caller reads as "nothing can be run here" and falls back to reading code.
    Like `run_tests`, this returns rather than raises.

    This is DR-170 Decision 5's per-project collection gate, at per-test grain.
    That record asks whether pytest "can be invoked and can collect the
    candidate node ids at all"; all-or-nothing is the difference between losing
    one test and losing every test.
    """
    config = config or SandboxConfig()
    requested = list(dict.fromkeys(test_ids))
    if not requested:
        return set()

    workspace = Path(tempfile.mkdtemp(prefix="acceptance-collect-"))
    try:
        return _collect_in_workspace(requested, project_root, config, workspace)
    except Exception:  # noqa: BLE001 - the contract is that this returns
        return set()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _collect_in_workspace(
    requested: list[str],
    project_root: Path,
    config: SandboxConfig,
    workspace: Path,
) -> set[str]:
    """Collect once for everything; on failure, collect file by file.

    The fast path is one subprocess. When it fails, pytest reports the error
    instead of the ids it managed to collect — so there is nothing to intersect
    and the whole set would be lost. Falling back to one call per test *file*
    contains the damage to the file that is actually broken, at the cost of one
    process per file, and only on the path where something is already wrong.

    Per file rather than per test id: the unit that fails to import is a module,
    and per id would be hundreds of processes to learn what tens already say.
    """
    plugin_dir = workspace / "plugin"
    plugin_dir.mkdir()
    shutil.copyfile(netblock.__file__, plugin_dir / f"{_PLUGIN_MODULE}.py")
    report_path = workspace / "outcomes.jsonl"
    report_path.touch()
    collected_path = workspace / "collected.txt"
    env = _sandbox_env(plugin_dir, report_path, config, project_root)
    env[netblock.COLLECTED_PATH_VAR] = str(collected_path)
    wanted = set(requested)

    exit_code, collected = _collect_once(
        requested, project_root, config, env, wanted, collected_path
    )
    if exit_code == 0:
        return collected

    # The joint collection failed, so the answer must be a set that collects
    # JOINTLY. Admitting each file that collects alone is not enough and is
    # actively misleading: every file here collects by itself, and the run still
    # dies when they are collected together, which is how #45's mutant runs each
    # lost all 326 tests after the baseline appeared healthy.
    #
    # So files are admitted one at a time, each kept only if the set still
    # collects with it. A file that conflicts with one already admitted is
    # dropped, and the loser is reported rather than lost.
    #
    # **Largest file first**, which decides who wins a conflict. Without it the
    # winner is whichever came first alphabetically, and on this repository that
    # meant keeping one test belonging to an archetype fixture and dropping the
    # twenty-one real tests it collided with. The objective a review actually
    # wants is to lose as little evidence as possible, and test count is the
    # only measure of that available without knowing anything about the project.
    # Ties break on the path, so the result does not depend on dict ordering.
    admitted_ids: list[str] = []
    admitted: set[str] = set()
    by_file = _by_file(requested)
    for path in sorted(by_file, key=lambda p: (-len(by_file[p]), p)):
        ids = by_file[path]
        candidate = admitted_ids + ids
        code, found = _collect_once(candidate, project_root, config, env, wanted, collected_path)
        if code == 0:
            admitted_ids = candidate
            admitted = found
    return admitted


def _by_file(test_ids: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for test_id in test_ids:
        grouped.setdefault(test_id.split("::", 1)[0], []).append(test_id)
    return grouped


def _collect_once(
    test_ids: list[str],
    project_root: Path,
    config: SandboxConfig,
    env: dict[str, str],
    wanted: set[str],
    collected_path: Path,
) -> tuple[int | None, set[str]]:
    """Ask pytest to collect `test_ids`; report its exit code and what it named.

    Collection imports every named module, which runs its top-level code, so it
    gets exactly the environment a real run gets — locked down, or the user's
    own under a test command. Importing a stranger's module is not a safe
    operation just because no test is executed afterwards.

    What pytest collected is read from the file the plugin writes, not from
    pytest's printed output. pytest prints ids relative to the directory it took
    as its root, which is wherever the nearest pytest configuration is — `api/`
    for a project kept in `api/` — while the review holds ids relative to the
    project root. Nothing matched, and every test was set aside, which is #405.
    The plugin writes ids relative to the project root instead.
    """
    collected_path.unlink(missing_ok=True)
    try:
        with _run_slot(config) as worker:
            aborted, _, exit_code = _spawn_and_wait(
                _pytest_command(config, ["--collect-only"], test_ids, project_root),
                cwd=project_root,
                env=_with_worker(env, worker),
                total_seconds=config.total_seconds,
            )
    except (OSError, subprocess.SubprocessError):
        return None, set()
    if aborted:
        return None, set()

    try:
        text = collected_path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    return exit_code, _match(text, wanted)


def _pytest_command(
    config: SandboxConfig, options: list[str], test_ids: list[str], project_root: Path
) -> list[str] | str:
    """The pytest invocation for `test_ids`, in whichever of the two forms applies.

    Without a test command, an argument list for the tool's own interpreter,
    with ids relative to the project root, which is the working directory.

    With one, a shell string: the user's command exactly as they gave it, then
    the plugin and the ids. The ids are absolute paths, because the command may
    change directory first — `cd api && .venv/bin/python -m pytest` — and an
    absolute path means the same file wherever pytest ends up running.

    Nothing else is added: the plugin, which is how outcomes and the per-test
    budget work; `no:cacheprovider`, so no `.pytest_cache` is written into the
    project; and `options`, which is `--collect-only` when listing tests. The
    user's command is theirs, and every extra flag is one more way it could
    behave differently from the run they know works.
    """
    arguments = [*options, "-p", _PLUGIN_MODULE, "-p", "no:cacheprovider"]
    if config.test_command is None:
        return [config.interpreter, "-m", "pytest", *arguments, *test_ids]
    root = project_root.resolve()
    absolute = [str(root / test_id) for test_id in test_ids]
    return " ".join([config.test_command, *(shlex.quote(a) for a in [*arguments, *absolute])])


#: One pool of numbered run slots per allowed width, shared by every run in
#: this process. Process-wide because the runs that must not overlap come from
#: different callers at once — the control run, and one thread per mutant.
_SLOT_POOLS: dict[int, queue.Queue[int]] = {}
_SLOT_POOLS_LOCK = threading.Lock()


@contextmanager
def _run_slot(config: SandboxConfig) -> Iterator[int | None]:
    """Hold one of `config.parallel_runs` numbered slots for the length of a run.

    Only under a test command. Those runs use the user's own services, and two
    of them against one database can corrupt each other's results, so no more
    run at once than the user said is safe — one, unless they said otherwise.
    The slot's number, 1 to `parallel_runs`, is what the run is told it is, so a
    project can give each concurrent run its own database.

    Locked-down runs take no slot: they share nothing, and limiting them would
    only slow down the case that is already safe.
    """
    if config.test_command is None:
        yield None
        return
    with _SLOT_POOLS_LOCK:
        pool = _SLOT_POOLS.get(config.parallel_runs)
        if pool is None:
            pool = queue.Queue()
            for number in range(1, config.parallel_runs + 1):
                pool.put(number)
            _SLOT_POOLS[config.parallel_runs] = pool
    number = pool.get()
    try:
        yield number
    finally:
        pool.put(number)


def _with_worker(env: dict[str, str], worker: int | None) -> dict[str, str]:
    if worker is None:
        return env
    return {**env, WORKER_VAR: str(worker)}


def _match(stdout: str, wanted: set[str]) -> set[str]:
    """Which wanted ids pytest named, allowing for parametrisation.

    Test discovery yields `file.py::test_name`. pytest names a parametrised test
    `file.py::test_name[case]`, once per case, and never the bare form — so an
    exact-match intersection silently drops every parametrised test. Ten of this
    repository's own candidates were lost that way before this existed.

    The wanted id is returned, not the parametrised one: the rest of the review
    identifies the test by the id discovery produced, and pytest accepts the
    bare form on a command line and runs all of its cases.
    """
    admitted: set[str] = set()
    for line in stdout.splitlines():
        reported = line.strip()
        if not reported:
            continue
        if reported in wanted:
            admitted.add(reported)
            continue
        base = reported.split("[", 1)[0]
        if "[" in reported and base in wanted:
            admitted.add(base)
    return admitted


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

    command = _pytest_command(config, [], requested, project_root)
    env = _sandbox_env(plugin_dir, report_path, config, project_root)

    with _run_slot(config) as worker:
        aborted, abort_reason, exit_code = _spawn_and_wait(
            command,
            cwd=project_root,
            env=_with_worker(env, worker),
            total_seconds=config.total_seconds,
        )

    observed = _fold_parametrised(_read_report(report_path), requested)
    unreached = _why_unreached(aborted, abort_reason, exit_code, observed)
    outcomes = [observed.get(test_id) or _not_started(test_id, unreached) for test_id in requested]
    return SandboxRunResult(
        outcomes=outcomes,
        aborted=aborted,
        abort_reason=abort_reason,
    )


def _fold_parametrised(
    observed: dict[str, TestOutcome], requested: list[str]
) -> dict[str, TestOutcome]:
    """Give each requested id an outcome, folding its parametrised cases into one.

    A caller asks for `file.py::test_name`. pytest runs every case of it and
    reports `file.py::test_name[case]` once per case, never the bare form — so
    matching by exact id loses every parametrised test, and it loses them as
    `not_started`, which reads as "the run never reached this" rather than "the
    runner could not recognise its own output". Ten of this repository's own
    candidate tests disappeared that way.

    **A failure anywhere means the test failed.** The caller asked one question
    — does this test pass against this code — and a test whose third case fails
    does not pass. Reporting it as passed because two cases passed would make a
    mutant that only breaks one case look survived.

    An incomplete case wins over passing cases for the same reason: nothing was
    established about a test whose cases did not all finish.
    """
    folded = dict(observed)
    for test_id in requested:
        if test_id in folded:
            continue
        cases = [
            outcome for reported, outcome in observed.items() if reported.startswith(f"{test_id}[")
        ]
        if not cases:
            continue
        failed = next((c for c in cases if c.kind is TestOutcomeKind.FAILED), None)
        incomplete = next((c for c in cases if not c.completed), None)
        chosen = failed or incomplete or cases[0]
        folded[test_id] = chosen.model_copy(update={"test_id": test_id})
    return folded


def _why_unreached(
    aborted: bool,
    abort_reason: str | None,
    exit_code: int | None,
    observed: dict[str, TestOutcome],
) -> str:
    """The reason a requested test ended with no outcome of its own.

    Three different things arrive here, and saying which is the whole point of
    the reason: the run was stopped by the whole-run budget, the run produced no
    report at all, or the run reported on other tests and never reached this
    one. Collapsing them into one sentence would make "tried and could not"
    indistinguishable from "did not try".
    """
    if aborted and abort_reason:
        return abort_reason
    if not observed:
        return (
            "the run produced no report at all (the test process exited with "
            f"{exit_code}), so nothing was observed about any requested test"
        )
    return "the run reported on other tests and ended without reaching this one"


def _import_roots(project_root: Path) -> list[str]:
    """Where `project_root`'s own code must be imported from, ahead of anything else.

    **Without this the mutation stage is worthless on most Python projects.** A
    project installed into its environment — `pip install -e .`, the normal way a
    `src/` layout is set up — resolves `import yourpackage` through an absolute
    path recorded at install time. Copying the tree and running pytest with the
    copy as the working directory does not change that: the tests run in the
    copy and import the code from the ORIGINAL. Every mutant then has no effect
    whatever, every defect is reported as survived, and the review confidently
    tells the builder their tests are weak on the strength of code it never
    altered.

    I verified this before fixing it: a mutant that removes a `raise` was applied
    to a copy, the test asserting that `raise` was run in the copy, and it
    passed. The interpreter there reported loading the package from the original
    working tree.

    `PYTHONPATH` is what corrects it, because Python honours it before
    site-packages and therefore before any path an install added. Both standard
    layouts are covered — the root for a flat project, `src/` for a src-layout
    one — and a directory that does not exist is simply omitted. A project whose
    importable code is somewhere else entirely is caught by the control run's
    faithfulness check rather than silently mis-reviewed.

    The baseline gets the same treatment, which is the point: the control and
    the mutants must differ only by the mutation.
    """
    roots = [project_root, project_root / "src"]
    return [str(path.resolve()) for path in roots if path.is_dir()]


def _sandbox_env(
    plugin_dir: Path, report_path: Path, config: SandboxConfig, project_root: Path
) -> dict[str, str]:
    """Build the subprocess environment.

    **Locked down**, with no test command: from an allowlist, never by
    inheriting. An allowlist rather than a denylist of credential-looking names:
    a denylist has to predict what a secret is called, and being wrong once is
    an execution-safety incident on someone else's repository.

    **Under a test command**: the user's whole environment, because that is
    what their tests run with every day — a `DATABASE_URL` is the reason the
    command exists. The user agreed to this when they set the command.
    """
    if config.test_command is None:
        env = {name: os.environ[name] for name in _INHERITED_ENV if name in os.environ}
        inherited_path: list[str] = []
        # The launching machine's per-user site-packages directory is on the
        # interpreter's path by default, and dropping `PYTHONPATH` from the
        # allowlist does not remove it. It is launch-side code the project under
        # review never asked for, so it is switched off explicitly.
        env["PYTHONNOUSERSITE"] = "1"
    else:
        env = dict(os.environ)
        inherited_path = [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
        env[netblock.ALLOW_NETWORK_VAR] = "1"
    # The project's own code first, the plugin after it: the plugin only has to
    # be importable, while the project's code has to win against an installed
    # copy of itself. Whatever the user had on the path comes last.
    env["PYTHONPATH"] = os.pathsep.join(
        [*_import_roots(project_root), str(plugin_dir), *inherited_path]
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env[netblock.REPORT_PATH_VAR] = str(report_path)
    env[netblock.PER_TEST_BUDGET_VAR] = repr(config.per_test_seconds)
    env[netblock.ID_ROOT_VAR] = str(project_root.resolve())
    return env


def passed_environment_names(config: SandboxConfig) -> list[str]:
    """The names of the environment variables a run passes to the project's tests.

    Names only, never values: the point is that a user can see a wrong
    `DATABASE_URL` is being passed, and printing its value would print its
    password. Only the variables from outside are listed; the ones this module
    sets for its own plugin are machinery, not the user's.
    """
    if config.test_command is None:
        return sorted(name for name in _INHERITED_ENV if name in os.environ)
    return sorted(os.environ)


def _spawn_and_wait(
    command: list[str] | str,
    cwd: Path,
    env: dict[str, str],
    total_seconds: float,
) -> tuple[bool, str | None, int | None]:
    """Run the command under the whole-run budget.

    A string is the user's test command and goes through the shell; a list is
    run directly. Either way the whole process group is killed at the budget,
    which matters more under the shell, where pytest is a child of the process
    we hold.

    Returns (aborted, abort reason, exit code). The exit code is `None` when the
    run was stopped rather than allowed to finish.
    """
    process = subprocess.Popen(
        command,
        shell=isinstance(command, str),
        cwd=str(cwd),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        exit_code = process.wait(timeout=total_seconds)
    except subprocess.TimeoutExpired:
        _terminate_group(process)
        return (
            True,
            f"the run exceeded its whole-run time budget of {total_seconds:g}s and was stopped",
            None,
        )
    return False, None, exit_code


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
                error_type=entry.get("error_type"),
                detail=entry.get("detail"),
            )
        except Exception:  # noqa: BLE001, S112 - a torn line is expected here
            continue
        observed.setdefault(outcome.test_id, outcome)
    return observed


def _not_started(test_id: str, reason: str) -> TestOutcome:
    return TestOutcome(test_id=test_id, kind=TestOutcomeKind.NOT_STARTED, reason=reason)


def _all_not_started(test_ids: list[str], reason: str) -> SandboxRunResult:
    return SandboxRunResult(outcomes=[_not_started(test_id, reason) for test_id in test_ids])
