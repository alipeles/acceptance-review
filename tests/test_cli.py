import json

import pytest

from acceptance.cli import main, run_check
from acceptance.config import RunConfig
from acceptance.review_store import ReviewStore


def test_check_json_emits_empty_structured_review(git_repo, fixture_task_path, capsys):
    exit_code = main(
        ["check", "--json", "--task", fixture_task_path, "--base", git_repo["base"], "--head", git_repo["head"]]
    )

    assert exit_code == 0
    review = json.loads(capsys.readouterr().out)
    assert review["mode"] == "local"
    assert review["reviewed_revision"] == git_repo["head"]
    assert review["mandate"] is None
    assert review["declaration"] is None
    # Diff endpoints are ingested; file-level diffing is still M2.
    assert review["change_set"]["base_revision"] == git_repo["base"]
    assert review["change_set"]["head_revision"] == git_repo["head"]
    assert review["change_set"]["files"] == []
    assert review["obligation_map"] == []
    assert review["findings"] == []
    assert review["limitations"] == []
    assert review["recommendation"] is None


def test_check_defaults_to_replay_mode_provenance(git_repo, fixture_task_path, capsys):
    exit_code = main(
        ["check", "--json", "--task", fixture_task_path, "--base", git_repo["base"], "--head", git_repo["head"]]
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
            "check", "--json",
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


def test_report_shell_renders_all_sections_present_and_empty(git_repo, fixture_task_path, capsys):
    exit_code = main(
        ["check", "--task", fixture_task_path, "--base", git_repo["base"], "--head", git_repo["head"]]
    )

    assert exit_code == 0
    out = capsys.readouterr().out
    # Every §16 section present...
    assert "Task completion: INDETERMINATE" in out
    assert "Obligation coverage:" in out
    assert "Test evidence:" in out
    assert "Unrequested changes:" in out
    assert "Recommended next instruction: (none)" in out
    # ...and empty in the walking skeleton.
    assert out.count("(none)") == 4  # 3 list sections + the next-instruction line


def test_check_persists_the_review_to_the_store(git_repo, fixture_task_path):
    from acceptance.review_store import ReviewStore

    assert main(
        ["check", "--task", fixture_task_path, "--base", git_repo["base"], "--head", git_repo["head"]]
    ) == 0

    # ReviewStore() defaults under the (chdir'd) repo; the review is keyed by head.
    stored = ReviewStore().read(git_repo["head"])
    assert stored is not None
    assert stored.reviewed_revision == git_repo["head"]
    assert stored.change_set.base_revision == git_repo["base"]


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


def test_run_check_accepts_an_explicit_repo_independent_of_cwd(
    git_repo_elsewhere, fixture_task_path, tmp_path
):
    """M-B0.2: the runner passes each case's repo as data, not via chdir."""
    review = run_check(
        task=fixture_task_path,
        base=git_repo_elsewhere["base"],
        head=git_repo_elsewhere["head"],
        config=RunConfig(),
        store=ReviewStore(tmp_path / "reviews"),
        repo=git_repo_elsewhere["path"],
    )

    assert review.reviewed_revision == git_repo_elsewhere["head"]
    assert review.change_set.base_revision == git_repo_elsewhere["base"]


def test_run_check_rejects_a_revision_missing_from_the_given_repo(
    git_repo_elsewhere, fixture_task_path, tmp_path
):
    from acceptance.cli import CliError

    with pytest.raises(CliError):
        run_check(
            task=fixture_task_path,
            base="not-a-real-revision",
            head=git_repo_elsewhere["head"],
            config=RunConfig(),
            store=ReviewStore(tmp_path / "reviews"),
            repo=git_repo_elsewhere["path"],
        )


# --- decompose subcommand (M1.2/M1.3 dogfood path) ---

def test_decompose_replay_without_transcript_fails_cleanly(
    fixture_task_path, tmp_path, monkeypatch, capsys
):
    # REPLAY mode with no recorded transcript must not call live; it errors out.
    # chdir to an empty dir so the relative transcript store is guaranteed empty.
    monkeypatch.chdir(tmp_path)
    exit_code = main(["decompose", "--task", fixture_task_path, "--mode", "replay"])

    assert exit_code == 1
    assert "model error" in capsys.readouterr().err


def test_decompose_missing_task_fails_cleanly(capsys):
    exit_code = main(["decompose", "--task", "does-not-exist.md", "--mode", "replay"])
    assert exit_code == 1
    assert "task file not found" in capsys.readouterr().err


def test_render_decomposition_lists_obligations_and_open_questions():
    from acceptance.cli import render_decomposition
    from acceptance.requirement.obligations import Decomposition
    from acceptance.review_state import Obligation, ObligationType, OpenQuestion

    result = Decomposition(
        obligations=[
            Obligation(
                id="ob-1",
                description="Do the thing.",
                type=ObligationType.FUNCTIONAL,
                importance="critical",
                explicit=True,
                observable_behavior="...",
            )
        ],
        open_questions=[OpenQuestion(id="q-1", question="How many?", importance="normal")],
    )

    rendered = render_decomposition(result)
    assert "[functional/explicit] ob-1: Do the thing." in rendered
    assert "? q-1: How many?" in rendered


# --- classify subcommand (M3.1 dogfood path) ---

def test_classify_replay_without_transcript_fails_cleanly(
    fixture_task_path, git_repo, monkeypatch, capsys
):
    # REPLAY with no transcript: the first live call (decompose) can't replay.
    monkeypatch.chdir(git_repo["path"])
    exit_code = main(
        ["classify", "--task", fixture_task_path, "--base", git_repo["base"],
         "--head", git_repo["head"], "--mode", "replay"]
    )
    assert exit_code == 1
    assert "model error" in capsys.readouterr().err


def test_render_classify_output():
    from acceptance.cli import render_classify
    from acceptance.coverage.classify import CoverageStatus, DiffRef, ImplementationCoverage
    from acceptance.coverage.unrequested import UnrequestedChange, UnrequestedChangeKind
    from acceptance.review_state import Obligation, ObligationType

    obligations = [
        Obligation(id="ob-1", description="Do the thing.", type=ObligationType.FUNCTIONAL,
                   importance="critical", explicit=True, observable_behavior="..."),
        Obligation(id="ob-2", description="Handle the edge.", type=ObligationType.BOUNDARY,
                   importance="normal", explicit=True, observable_behavior="..."),
    ]
    coverages = [
        ImplementationCoverage(
            obligation_id="ob-1", status=CoverageStatus.ADDRESSED, rationale="done",
            diff_refs=[DiffRef(file="pkg.py", hunk_header="@@ -1 +1 @@")],
        ),
        ImplementationCoverage(
            obligation_id="ob-2", status=CoverageStatus.NOT_ADDRESSED, rationale="missing",
        ),
    ]
    unrequested = [
        UnrequestedChange(
            kind=UnrequestedChangeKind.PUBLIC_INTERFACE,
            rationale="checkout signature changed",
            diff_refs=[DiffRef(file="cart.py", hunk_header="@@ -1 +1 @@")],
        )
    ]

    rendered = render_classify(obligations, coverages, unrequested)
    assert "[addressed] ob-1: Do the thing." in rendered
    assert "pkg.py" in rendered
    assert "[not_addressed] ob-2: Handle the edge." in rendered
    assert "no corresponding change" in rendered
    assert "Unrequested changes" in rendered
    assert "[public_interface] checkout signature changed" in rendered
    assert "cart.py" in rendered
