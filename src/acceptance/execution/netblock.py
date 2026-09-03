"""The pytest plugin the sandbox loads inside the run, before any test imports.

**This module imports nothing from `acceptance` on purpose.** It is copied into
a temporary directory and loaded by the project's own interpreter with `-p`,
which will not have this project installed. Keep it standalone and stdlib-only.

It does three things, all of which have to happen inside the run rather than
around it:

1. Blocks outbound network before the first test module is imported. `-p`
   plugins load before collection, which is the earliest hook available.
2. Enforces the per-test time budget, which only the process running the test
   can interrupt.
3. Writes one line per test to a report file as each finishes, so that a run
   killed by the whole-run budget still leaves the outcomes it did observe.
"""

from __future__ import annotations

import json
import os
import signal
import socket

import pytest  # available by definition: this module is loaded by pytest

#: Written into the traceback so the runner can tell the three failure kinds
#: apart without parsing pytest's prose.
NETWORK_MARKER = "ACCEPTANCE_NETWORK_BLOCKED"
TIMEOUT_MARKER = "ACCEPTANCE_TEST_TIMEOUT"

#: Environment variables the runner sets. Passed this way rather than as
#: command-line options so that the plugin adds no pytest arguments, which
#: keeps the invocation to the named tests and nothing else.
REPORT_PATH_VAR = "ACCEPTANCE_SANDBOX_REPORT"
PER_TEST_BUDGET_VAR = "ACCEPTANCE_SANDBOX_PER_TEST_SECONDS"

#: A local socket is not network egress, and forbidding it breaks unrelated
#: machinery — `multiprocessing` uses it on some platforms. Everything else is
#: refused, loopback included: a test reaching a service on localhost is
#: reaching a service.
_ALLOWED_FAMILIES = frozenset(
    family for family in (getattr(socket, "AF_UNIX", None),) if family is not None
)


class NetworkBlocked(RuntimeError):
    """Raised in place of any outbound connection a test attempts."""


class TestTimedOut(BaseException):
    """Raised in the test's own frame when its time budget expires.

    Derived from `BaseException` so that a test with a bare `except Exception`
    around the call under test cannot swallow its own timeout.
    """


def _refuse(what: str) -> NetworkBlocked:
    return NetworkBlocked(f"{NETWORK_MARKER}: {what} is blocked inside the acceptance sandbox")


def install_network_block() -> None:
    """Replace the outbound entry points in `socket` with refusals.

    The block is at the Python socket layer, not the operating system's. A C
    extension that opens a socket without going through `socket` is not caught.
    That limit is real and stated rather than papered over.
    """
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def connect(self, address, *args, **kwargs):  # type: ignore[no-untyped-def]
        if self.family in _ALLOWED_FAMILIES:
            return original_connect(self, address, *args, **kwargs)
        raise _refuse(f"connecting to {address!r}")

    def connect_ex(self, address, *args, **kwargs):  # type: ignore[no-untyped-def]
        if self.family in _ALLOWED_FAMILIES:
            return original_connect_ex(self, address, *args, **kwargs)
        raise _refuse(f"connecting to {address!r}")

    def getaddrinfo(host, port, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise _refuse(f"resolving {host!r}")

    def create_connection(address, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise _refuse(f"connecting to {address!r}")

    socket.socket.connect = connect  # type: ignore[method-assign]
    socket.socket.connect_ex = connect_ex  # type: ignore[method-assign]
    socket.getaddrinfo = getaddrinfo  # type: ignore[assignment]
    socket.create_connection = create_connection  # type: ignore[assignment]


class _Reporter:
    """Accumulates each test's outcome and flushes it the moment it is final.

    Flushing per test rather than at the end is what makes the whole-run budget
    survivable: when the runner kills the process group, the tests that already
    finished have already been written down.
    """

    def __init__(self, path: str | None) -> None:
        # `None` when the plugin was loaded without a report path. It still
        # accumulates, so nothing else has to care whether reporting is on.
        self._path = path
        self._pending: dict[str, tuple[str, str | None]] = {}

    def note(self, node_id: str, kind: str, reason: str | None = None) -> None:
        # Setup and teardown can each fail after the call phase already
        # recorded something. First non-passing observation wins, because it is
        # the one that explains the test.
        existing = self._pending.get(node_id)
        if existing is not None and existing[0] != "passed":
            return
        self._pending[node_id] = (kind, reason)

    def flush(self, node_id: str) -> None:
        entry = self._pending.pop(node_id, None)
        if entry is None or self._path is None:
            return
        kind, reason = entry
        line = json.dumps(
            {"test_id": node_id, "kind": kind, "reason": reason},
            sort_keys=True,
        )
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def _classify(report) -> tuple[str, str | None]:  # type: ignore[no-untyped-def]
    text = report.longreprtext or ""
    if NETWORK_MARKER in text:
        return "network_blocked", "the test attempted to reach the network"
    if TIMEOUT_MARKER in text:
        return "timed_out", "the test exceeded its own time budget"
    return "failed", None


class SandboxPlugin:
    def __init__(self, reporter: _Reporter, per_test_seconds: float | None) -> None:
        self._reporter = reporter
        self._per_test_seconds = per_test_seconds

    # --- the per-test budget -------------------------------------------------

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):  # type: ignore[no-untyped-def]
        """Arm a real-time alarm around one test, and disarm it afterwards.

        A wrapper rather than a plain hook: the clock has to be running while
        pytest executes the test, which is what the wrapper's `yield` spans.
        """
        if not self._can_time_out():
            yield
            return
        previous = signal.signal(signal.SIGALRM, self._on_alarm)
        signal.setitimer(signal.ITIMER_REAL, self._per_test_seconds)
        try:
            yield
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)

    def _can_time_out(self) -> bool:
        return (
            self._per_test_seconds is not None
            and self._per_test_seconds > 0
            and _can_arm_an_alarm()
        )

    @staticmethod
    def _on_alarm(signum, frame):  # type: ignore[no-untyped-def]
        raise TestTimedOut(f"{TIMEOUT_MARKER}: the test exceeded its per-test time budget")

    # --- the report ----------------------------------------------------------

    def pytest_runtest_logreport(self, report) -> None:  # type: ignore[no-untyped-def]
        if report.skipped:
            # A skip is `not_started` either way — no verdict about the test was
            # observed — but the reason has to say which kind it was. A test
            # that reached its own body and called `pytest.skip()` *did* run,
            # and recording that as "never started" erases the distinction this
            # outcome exists to keep.
            ran_first = report.when == "call"
            self._reporter.note(
                report.nodeid,
                "not_started",
                (
                    "the test ran and skipped itself, so no verdict was observed"
                    if ran_first
                    else "the project's own suite skipped this test before it ran"
                ),
            )
            return
        if report.failed:
            kind, reason = _classify(report)
            self._reporter.note(report.nodeid, kind, reason)
            return
        if report.when == "call" and report.passed:
            self._reporter.note(report.nodeid, "passed", None)

    def pytest_runtest_logfinish(self, nodeid, location=None) -> None:  # type: ignore[no-untyped-def]
        self._reporter.flush(nodeid)


def pytest_configure(config) -> None:  # type: ignore[no-untyped-def]
    install_network_block()

    # A missing report path means reporting has nowhere to go. It must NOT mean
    # the rest of the plugin is skipped: an early return here would leave the
    # per-test time budget unarmed while the run still looked sandboxed, which
    # is the half-protected state this package exists to rule out.
    report_path = os.environ.get(REPORT_PATH_VAR) or None

    raw_budget = os.environ.get(PER_TEST_BUDGET_VAR, "")
    try:
        per_test_seconds: float | None = float(raw_budget) if raw_budget else None
    except ValueError:
        per_test_seconds = None

    # A budget that was asked for and cannot be enforced is refused, not
    # ignored. The alarm needs `signal.setitimer`, which not every platform
    # has; running anyway would produce a result that looks time-bounded and is
    # not. DR-170 Decision 1's cost asymmetry applies — a declined run is
    # recorded and arguable, an unbounded one is an execution-safety incident.
    if per_test_seconds and per_test_seconds > 0 and not _can_arm_an_alarm():
        raise pytest.UsageError(
            "a per-test time budget was requested but this platform has no "
            "signal.setitimer, so the budget cannot be enforced; the sandbox "
            "declines to run rather than run unbounded"
        )

    config.pluginmanager.register(
        SandboxPlugin(_Reporter(report_path), per_test_seconds),
        name="acceptance-sandbox",
    )


def _can_arm_an_alarm() -> bool:
    return hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")
