"""The CLI hands the pipeline execution settings, and asks nobody whether to run.

**There is no `--execute` flag and no override for failing tests.** Whether
running the project's tests is worth doing is the review's own decision
(`mutation/settings.py::decide_execution`), and a red candidate test is set
aside rather than stopping anything — the human's rulings of 2026-09-18.

These assert what `run_check` was actually given, not that the parser accepted
some words: a flag that parses but never arrives is the same shape of hole as a
helper the pipeline never calls.
"""

from __future__ import annotations

import pytest

from acceptance import cli
from acceptance.mutation.settings import ExecutionSettings


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


class TestTheSettingsArrive:
    def test_the_pipeline_is_given_settings_to_decide_with(self, captured_settings):
        """Not `None`: the review cannot decide whether a run is worth doing
        without the budgets a run would use."""
        cli.main(_argv())
        assert isinstance(captured_settings["execution"], ExecutionSettings)

    def test_the_settings_carry_no_on_switch(self, captured_settings):
        """The decision is computed per review, so there is no field here for
        an operator to set — and none for the CLI to pass."""
        cli.main(_argv())
        fields = set(type(captured_settings["execution"]).model_fields)
        assert "enabled" not in fields
        assert "allow_failing_tests" not in fields

    def test_verification_is_off_by_default(self, captured_settings):
        """It is below its adoption bar (#335), and while it is off no
        observation can count — which is what makes a run not worth doing."""
        cli.main(_argv())
        assert captured_settings["execution"].verify_edits is False


class TestTheRetiredFlags:
    @pytest.mark.parametrize("flag", ["--execute", "--allow-failing-tests"])
    def test_the_flag_is_gone(self, flag, capsys, monkeypatch):
        """Refused rather than silently accepted, so a caller still passing it
        learns the decision moved rather than believing they switched something
        on."""
        monkeypatch.setattr(cli, "run_check", lambda *a, **k: 0)
        with pytest.raises(SystemExit):
            cli.main(_argv(flag))
        assert "unrecognized arguments" in capsys.readouterr().err
