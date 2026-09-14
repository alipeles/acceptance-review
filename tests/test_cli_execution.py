"""The `--execute` flags reach the pipeline, and a halt is not an error.

A flag that parses but never arrives is the same shape of hole as a helper the
pipeline never calls, so these assert what `run_check` was actually given rather
than that the parser accepted the words.
"""

from __future__ import annotations

import pytest

from acceptance import cli
from acceptance.mutation.baseline import Baseline
from acceptance.mutation.settings import ReviewHalted


@pytest.fixture
def captured_settings(monkeypatch):
    """Intercept `run_check` and keep the `ExecutionSettings` it was handed."""
    seen: dict = {}

    def fake_run_check(*_args, **kwargs):
        seen["execution"] = kwargs.get("execution")
        raise cli.CliError("stopped after capturing the settings")

    monkeypatch.setattr(cli, "run_check", fake_run_check)
    return seen


def _argv(*extra: str) -> list[str]:
    return ["check", "--task", "t.md", "--base", "HEAD~1", *extra]


class TestTheFlagsArrive:
    def test_execution_is_off_without_the_flag(self, captured_settings):
        cli.main(_argv())
        assert captured_settings["execution"].enabled is False

    def test_execute_turns_it_on(self, captured_settings):
        cli.main(_argv("--execute"))
        assert captured_settings["execution"].enabled is True

    def test_the_override_is_off_by_default(self, captured_settings):
        cli.main(_argv("--execute"))
        assert captured_settings["execution"].allow_failing_tests is False

    def test_allow_failing_tests_arrives(self, captured_settings):
        cli.main(_argv("--execute", "--allow-failing-tests"))
        assert captured_settings["execution"].allow_failing_tests is True


class TestAHaltIsReportedNotRaised:
    @pytest.fixture
    def halting(self, monkeypatch):
        baseline = Baseline(
            halted=True,
            halt_reason="1 candidate test(s) fail against the code as delivered",
            set_aside=[
                {
                    "test_id": "tests/test_a.py::test_broken",
                    "kind": "failed",
                    "reason": "the test failed against the code as delivered",
                }
            ],
        )

        def fake_run_check(*_args, **_kwargs):
            raise ReviewHalted(baseline)

        monkeypatch.setattr(cli, "run_check", fake_run_check)

    def test_the_exit_code_distinguishes_a_halt_from_a_failure(self, halting, capsys):
        """Exit 2, not 1. Nothing failed — the review declined to spend on a
        control that would prove nothing — and a caller scripting this has to be
        able to tell the two apart."""
        assert cli.main(_argv("--execute")) == 2

    def test_the_failing_test_is_named_on_stderr(self, halting, capsys):
        cli.main(_argv("--execute"))
        err = capsys.readouterr().err
        assert "tests/test_a.py::test_broken" in err

    def test_stdout_carries_no_report(self, halting, capsys):
        """A halt must not be mistakable for a clean review."""
        cli.main(_argv("--execute"))
        assert capsys.readouterr().out == ""

    def test_the_override_is_suggested(self, halting, capsys):
        cli.main(_argv("--execute"))
        assert "--allow-failing-tests" in capsys.readouterr().err
