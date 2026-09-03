"""What the sandbox actually does, observed by running it.

These tests spawn a real pytest against a throwaway project. That is deliberate
and it is the point: the two properties #43 exists to guarantee — a test cannot
reach the network, and the run stops when the budget expires — are properties of
a process, and a unit test over a mocked subprocess would demonstrate neither.
The project's own rule applies to its own tests: a test that would pass with the
behaviour absent is not evidence.
"""

import os
import sys
import textwrap
import time
from pathlib import Path

import pytest

from acceptance.execution.outcome import TestOutcomeKind
from acceptance.execution.sandbox import SandboxConfig, run_tests

pytestmark = pytest.mark.skipif(
    os.name != "posix", reason="the sandbox's process-group control is POSIX-only"
)


def _project(tmp_path: Path, body: str) -> Path:
    """A throwaway project holding one test module, and nothing else."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "test_subject.py").write_text(textwrap.dedent(body), encoding="utf-8")
    return root


def _fast(**overrides) -> SandboxConfig:
    defaults = {"interpreter": sys.executable, "per_test_seconds": 10.0}
    defaults.update(overrides)
    return SandboxConfig(**defaults)


# --- the network block -------------------------------------------------------


def test_a_test_that_opens_a_connection_is_reported_as_blocked(tmp_path):
    root = _project(
        tmp_path,
        """
        import socket

        def test_reaches_out():
            socket.create_connection(("example.com", 80), timeout=5)
        """,
    )
    result = run_tests(["test_subject.py::test_reaches_out"], root, _fast())

    outcome = result.outcome_for("test_subject.py::test_reaches_out")
    assert outcome.kind is TestOutcomeKind.NETWORK_BLOCKED
    assert "network" in outcome.reason


def test_a_test_that_resolves_a_hostname_is_reported_as_blocked(tmp_path):
    root = _project(
        tmp_path,
        """
        import socket

        def test_resolves():
            socket.getaddrinfo("example.com", 80)
        """,
    )
    result = run_tests(["test_subject.py::test_resolves"], root, _fast())

    assert (
        result.outcome_for("test_subject.py::test_resolves").kind is TestOutcomeKind.NETWORK_BLOCKED
    )


def test_the_block_is_distinguished_from_an_ordinary_failure(tmp_path):
    """A failing test and a blocked test must not land on the same outcome.

    Without this the network block is unfalsifiable: everything it stops looks
    like a test that was going to fail anyway.
    """
    root = _project(
        tmp_path,
        """
        def test_just_fails():
            assert 1 == 2
        """,
    )
    result = run_tests(["test_subject.py::test_just_fails"], root, _fast())

    outcome = result.outcome_for("test_subject.py::test_just_fails")
    assert outcome.kind is TestOutcomeKind.FAILED
    assert outcome.reason is None


def test_a_test_that_touches_no_network_still_passes(tmp_path):
    root = _project(
        tmp_path,
        """
        def test_arithmetic():
            assert 2 + 2 == 4
        """,
    )
    result = run_tests(["test_subject.py::test_arithmetic"], root, _fast())

    assert result.outcome_for("test_subject.py::test_arithmetic").kind is TestOutcomeKind.PASSED
    assert not result.aborted


# --- the time budgets --------------------------------------------------------


def test_a_test_that_outlasts_its_own_budget_is_reported_as_timed_out(tmp_path):
    root = _project(
        tmp_path,
        """
        import time

        def test_sleeps():
            time.sleep(30)
        """,
    )
    result = run_tests(
        ["test_subject.py::test_sleeps"],
        root,
        _fast(per_test_seconds=1.0, total_seconds=60.0),
    )

    outcome = result.outcome_for("test_subject.py::test_sleeps")
    assert outcome.kind is TestOutcomeKind.TIMED_OUT
    assert "time budget" in outcome.reason
    assert not result.aborted, "one slow test is not a failed run"


def test_the_whole_run_budget_aborts_and_leaves_no_test_unaccounted_for(tmp_path):
    root = _project(
        tmp_path,
        """
        import time

        def test_first():
            assert True

        def test_then_hangs():
            time.sleep(60)

        def test_never_reached():
            assert True
        """,
    )
    requested = [
        "test_subject.py::test_first",
        "test_subject.py::test_then_hangs",
        "test_subject.py::test_never_reached",
    ]
    result = run_tests(requested, root, _fast(per_test_seconds=45.0, total_seconds=6.0))

    assert result.aborted
    assert "whole-run time budget" in result.abort_reason

    assert [o.test_id for o in result.outcomes] == requested
    assert result.outcome_for("test_subject.py::test_first").kind is TestOutcomeKind.PASSED, (
        "an outcome observed before the abort survives it"
    )
    assert (
        result.outcome_for("test_subject.py::test_never_reached").kind
        is TestOutcomeKind.NOT_STARTED
    )
    assert result.outcome_for("test_subject.py::test_never_reached").reason


def test_the_abort_leaves_nothing_executing(tmp_path):
    """A test's own child process must die with the run, not outlive it.

    The child is the whole point. Killing the pytest process alone would pass a
    test whose slow work runs inside pytest, because that work dies with its
    process either way — so this test spawns a grandchild that ticks a file, and
    fails unless the whole process group is stopped.
    """
    marker = tmp_path / "ticks"
    ticker = (
        "import time\n"
        f"for _ in range(600):\n"
        f"    open({str(marker)!r}, 'a').write('x')\n"
        "    time.sleep(0.1)\n"
    )
    root = _project(
        tmp_path,
        f"""
        import subprocess
        import sys
        import time

        def test_spawns_a_child_and_waits():
            subprocess.Popen([sys.executable, "-c", {ticker!r}])
            time.sleep(60)
        """,
    )
    run_tests(
        ["test_subject.py::test_spawns_a_child_and_waits"],
        root,
        _fast(per_test_seconds=45.0, total_seconds=3.0),
    )

    assert marker.exists(), "the child never started; the test proves nothing"
    settled = marker.stat().st_size
    time.sleep(1.5)
    assert marker.stat().st_size == settled, "the test's child process outlived the aborted run"


# --- what the run may see ----------------------------------------------------


def test_the_launching_environment_s_credentials_do_not_reach_the_test(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-never-be-visible")
    monkeypatch.setenv("SOME_PRIVATE_TOKEN", "also-secret")

    root = _project(
        tmp_path,
        """
        import os

        def test_sees_no_secrets():
            assert "OPENAI_API_KEY" not in os.environ
            assert "SOME_PRIVATE_TOKEN" not in os.environ
        """,
    )
    result = run_tests(["test_subject.py::test_sees_no_secrets"], root, _fast())

    assert (
        result.outcome_for("test_subject.py::test_sees_no_secrets").kind is TestOutcomeKind.PASSED
    )


def test_only_the_named_tests_run(tmp_path):
    root = _project(
        tmp_path,
        """
        def test_named():
            assert True

        def test_not_named():
            raise AssertionError("this test was not requested and must not run")
        """,
    )
    result = run_tests(["test_subject.py::test_named"], root, _fast())

    assert [o.test_id for o in result.outcomes] == ["test_subject.py::test_named"]
    assert result.outcome_for("test_subject.py::test_not_named") is None


def test_an_empty_request_runs_nothing(tmp_path):
    """pytest with no node ids runs the whole suite. The runner must not.

    Asserting the result is empty proves nothing here — with no ids requested,
    the result is empty whether or not pytest ran. The evidence is the marker
    file, written when the project's test module is merely imported, so it
    catches collection as well as execution.
    """
    marker = tmp_path / "was-collected"
    root = _project(
        tmp_path,
        f"""
        open({str(marker)!r}, "w").write("collected")

        def test_would_be_collected():
            assert True
        """,
    )
    result = run_tests([], root, _fast())

    assert not marker.exists(), "an empty request reached pytest and it collected"
    assert result.outcomes == []
    assert not result.aborted


def test_the_launch_machine_s_user_site_packages_are_switched_off(tmp_path):
    """Dropping PYTHONPATH is not enough: user site-packages is on the path anyway.

    It is launch-side code the project under review never asked for, and no
    inherited environment variable is needed for it to be reachable.

    **What this shows and what it does not.** It asserts the switch is set, not
    that the switch works. Asserting `site.ENABLE_USER_SITE` is false would be
    the stronger claim and it is not available here: this suite runs under a
    virtualenv, where user site is already disabled, so that assertion passes
    with the fix removed. Defect injection caught exactly that. This is the
    honest weaker test rather than one that looks stronger and proves less.
    """
    root = _project(
        tmp_path,
        """
        import os

        def test_user_site_is_disabled():
            assert os.environ.get("PYTHONNOUSERSITE") == "1"
        """,
    )
    result = run_tests(["test_subject.py::test_user_site_is_disabled"], root, _fast())

    assert (
        result.outcome_for("test_subject.py::test_user_site_is_disabled").kind
        is TestOutcomeKind.PASSED
    )


def test_a_test_that_skips_itself_is_not_reported_as_never_started(tmp_path):
    """A runtime skip means the test ran. The reason has to say so.

    Both a runtime skip and a collection-time skip are `not_started`, because
    neither observed a verdict — but recording a test that reached its own body
    as "never started" erases the distinction the outcome exists to carry.
    """
    root = _project(
        tmp_path,
        """
        import pytest

        def test_skips_itself():
            pytest.skip("decided at runtime")

        @pytest.mark.skip(reason="decided before running")
        def test_skipped_before_running():
            raise AssertionError("never reached")
        """,
    )
    result = run_tests(
        [
            "test_subject.py::test_skips_itself",
            "test_subject.py::test_skipped_before_running",
        ],
        root,
        _fast(),
    )

    ran = result.outcome_for("test_subject.py::test_skips_itself")
    assert ran.kind is TestOutcomeKind.NOT_STARTED
    assert "ran and skipped itself" in ran.reason

    never_ran = result.outcome_for("test_subject.py::test_skipped_before_running")
    assert never_ran.kind is TestOutcomeKind.NOT_STARTED
    assert "before it ran" in never_ran.reason
    assert ran.reason != never_ran.reason


def test_the_per_test_budget_still_applies_without_a_report_path(tmp_path, monkeypatch):
    """Loaded with no report path, the plugin must still arm the clock.

    Reporting having nowhere to go is not a reason to leave the run
    unprotected — a half-sandboxed run that looks sandboxed is the state this
    package exists to rule out.
    """
    from acceptance.execution import netblock

    monkeypatch.delenv(netblock.REPORT_PATH_VAR, raising=False)
    monkeypatch.setenv(netblock.PER_TEST_BUDGET_VAR, "5")

    registered = {}

    class _Config:
        class pluginmanager:  # mimics pytest's attribute shape
            @staticmethod
            def register(plugin, name):
                registered[name] = plugin

    netblock.pytest_configure(_Config())

    plugin = registered["acceptance-sandbox"]
    assert plugin._can_time_out(), "the per-test budget was left unarmed"


def test_a_run_that_reports_nothing_says_so_rather_than_looking_untried(tmp_path):
    """Three things become `not_started`, and the reason must tell them apart."""
    root = _project(tmp_path, "def test_anything():\n    assert True\n")

    result = run_tests(
        ["test_subject.py::test_anything"],
        root,
        _fast(interpreter=str(tmp_path / "no-such-interpreter")),
    )

    reason = result.outcome_for("test_subject.py::test_anything").reason
    assert "no report" in reason or "could not run" in reason
    assert "reached this one" not in reason


# --- the contract that it returns rather than raises -------------------------


def test_an_unusable_interpreter_yields_outcomes_rather_than_an_exception(tmp_path):
    root = _project(tmp_path, "def test_anything():\n    assert True\n")

    result = run_tests(
        ["test_subject.py::test_anything"],
        root,
        _fast(interpreter=str(tmp_path / "no-such-interpreter")),
    )

    outcome = result.outcome_for("test_subject.py::test_anything")
    assert outcome.kind is TestOutcomeKind.NOT_STARTED
    assert outcome.reason


def test_a_missing_project_directory_yields_outcomes_rather_than_an_exception(
    tmp_path,
):
    result = run_tests(["test_subject.py::test_anything"], tmp_path / "does-not-exist", _fast())

    assert result.outcome_for("test_subject.py::test_anything").kind is TestOutcomeKind.NOT_STARTED


def test_a_test_that_does_not_exist_is_not_started_rather_than_dropped(tmp_path):
    root = _project(tmp_path, "def test_present():\n    assert True\n")

    result = run_tests(["test_subject.py::test_absent"], root, _fast())

    outcome = result.outcome_for("test_subject.py::test_absent")
    assert outcome.kind is TestOutcomeKind.NOT_STARTED
    assert outcome.reason


# --- the configuration -------------------------------------------------------


def test_a_budget_of_zero_or_less_is_refused():
    with pytest.raises(ValueError, match="greater than zero"):
        SandboxConfig(per_test_seconds=0)
    with pytest.raises(ValueError, match="greater than zero"):
        SandboxConfig(total_seconds=-1)


def test_the_interpreter_must_be_named():
    with pytest.raises(ValueError, match="must be named"):
        SandboxConfig(interpreter="  ")


def test_the_defaults_come_from_configuration_not_from_the_project(tmp_path):
    """Nothing in a project can move the budgets or choose the interpreter."""
    (tmp_path / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\ntimeout = 9999\n", encoding="utf-8"
    )
    (tmp_path / "tox.ini").write_text("[testenv]\nbasepython = /nope\n", encoding="utf-8")

    config = SandboxConfig()

    assert config.interpreter == sys.executable
    assert config.per_test_seconds == 30.0
    assert config.total_seconds == 300.0
