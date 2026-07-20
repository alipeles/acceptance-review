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


def test_check_defaults_to_replay_mode_provenance(git_repo, fixture_task_path, capsys):
    exit_code = main(
        ["check", "--task", fixture_task_path, "--base", git_repo["base"], "--head", git_repo["head"]]
    )

    assert exit_code == 0
    review = json.loads(capsys.readouterr().out)
    # Default mode is replay so the CLI never issues a live call unbidden.
    assert review["provenance"]["determinism_mode"] == "replay"
    assert review["provenance"]["temperature"] == 0.0
    assert review["provenance"]["seed"] is None


def test_check_records_determinism_flags_in_provenance(git_repo, fixture_task_path, capsys):
    exit_code = main(
        [
            "check",
            "--task", fixture_task_path,
            "--base", git_repo["base"],
            "--head", git_repo["head"],
            "--model", "openai/gpt-5",
            "--mode", "record",
            "--seed", "7",
            "--temperature", "0.4",
        ]
    )

    assert exit_code == 0
    provenance = json.loads(capsys.readouterr().out)["provenance"]
    assert provenance == {
        "determinism_mode": "record",
        "model": "openai/gpt-5",
        "temperature": 0.4,
        "seed": 7,
    }


def test_check_rejects_unknown_mode(git_repo, fixture_task_path):
    with pytest.raises(SystemExit):
        main(
            [
                "check",
                "--task", fixture_task_path,
                "--base", git_repo["base"],
                "--head", git_repo["head"],
                "--mode", "live",
            ]
        )


def test_two_runs_over_the_same_input_are_byte_identical(git_repo, fixture_task_path, capsys):
    args = [
        "check", "--task", fixture_task_path, "--base", git_repo["base"], "--head", git_repo["head"]
    ]

    assert main(args) == 0
    first = capsys.readouterr().out
    assert main(args) == 0
    second = capsys.readouterr().out

    assert first == second


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
