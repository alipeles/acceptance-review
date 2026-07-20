import json

import pytest

from acceptance.cli import main


def test_check_exits_zero_with_empty_structured_review(git_repo, fixture_task_path, capsys):
    exit_code = main(
        ["check", "--task", fixture_task_path, "--base", git_repo["base"], "--head", git_repo["head"]]
    )

    assert exit_code == 0
    review = json.loads(capsys.readouterr().out)
    assert review["mode"] == "local"
    assert review["reviewed_revision"] == git_repo["head"]
    assert review["mandate"] is None
    assert review["declaration"] is None
    assert review["change_set"] is None
    assert review["obligation_map"] == []
    assert review["findings"] == []
    assert review["limitations"] == []
    assert review["recommendation"] is None


def test_check_fails_cleanly_on_missing_task_file(git_repo, capsys):
    exit_code = main(
        ["check", "--task", "does-not-exist.md", "--base", git_repo["base"], "--head", git_repo["head"]]
    )

    assert exit_code == 1
    assert "task file not found" in capsys.readouterr().err


def test_check_fails_cleanly_on_unresolvable_revision(git_repo, fixture_task_path, capsys):
    exit_code = main(
        ["check", "--task", fixture_task_path, "--base", "not-a-real-revision", "--head", git_repo["head"]]
    )

    assert exit_code == 1
    assert "revision not found" in capsys.readouterr().err


def test_check_requires_all_flags(fixture_task_path):
    with pytest.raises(SystemExit):
        main(["check", "--task", fixture_task_path])
