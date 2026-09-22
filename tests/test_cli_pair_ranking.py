"""The CLI's early-stop setting reaches the pair judge (#348).

Both hops are pinned, because either one dropping the value leaves a flag that
parses and changes nothing: the command line into `RunConfig`, and `RunConfig`
into `run_review`.
"""

from __future__ import annotations

import pytest

from acceptance import cli
from acceptance.config import RunConfig
from acceptance.review_store import ReviewStore
from tests.support import client_finding_nothing


@pytest.fixture
def captured_config(monkeypatch):
    seen: dict = {}

    def fake_run_check(_task, _base, _head, config, *_args, **_kwargs):
        seen["config"] = config
        raise cli.CliError("stopped after capturing the config")

    monkeypatch.setattr(cli, "run_check", fake_run_check)
    return seen


def _argv(*extra: str) -> list[str]:
    return ["check", "--task", "t.md", "--base", "HEAD~1", *extra]


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ((), 1),
        (("--stop-after-kills", "3"), 3),
        (("--full-pair-sweep",), None),
        (("--stop-after-kills", "3", "--full-pair-sweep"), None),
    ],
)
def test_the_command_line_sets_the_stop_number(captured_config, extra, expected):
    cli.main(_argv(*extra))
    assert captured_config["config"].stop_after_kills == expected


@pytest.mark.parametrize("stop", [None, 2])
def test_run_check_hands_the_stop_number_to_the_pipeline(
    monkeypatch, git_repo_elsewhere, fixture_task_path, tmp_path, stop
):
    seen: dict = {}

    def fake_run_review(**kwargs):
        seen.update(kwargs)
        raise cli.CliError("stopped after capturing the pipeline arguments")

    monkeypatch.setattr(cli, "run_review", fake_run_review)
    with pytest.raises(cli.CliError):
        cli.run_check(
            task=fixture_task_path,
            base=git_repo_elsewhere["base"],
            head=git_repo_elsewhere["head"],
            config=RunConfig(stop_after_kills=stop),
            store=ReviewStore(tmp_path / "reviews"),
            repo=git_repo_elsewhere["path"],
            client=client_finding_nothing(),
        )
    assert seen["stop_after_kills"] == stop
