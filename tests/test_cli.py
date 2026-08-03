import json

import pytest

from acceptance.cli import main, run_check
from acceptance.config import DEFAULT_SEED, RunConfig
from acceptance.review_store import ReviewStore
from tests.support import client_finding_nothing


def test_check_json_emits_a_structured_review(git_repo, fixture_task_path, capsys, stub_model):
    """--json emits the full structured Review. With a checker that finds
    nothing, the analysis fields are empty but the shape is complete."""
    exit_code = main(
        ["check", "--json", "--task", fixture_task_path, "--base", git_repo["base"], "--head", git_repo["head"]]
    )

    assert exit_code == 0
    review = json.loads(capsys.readouterr().out)
    assert review["mode"] == "local"
    assert review["reviewed_revision"] == git_repo["head"]
    assert review["mandate"] is None
    assert review["change_set"]["base_revision"] == git_repo["base"]
    assert review["change_set"]["head_revision"] == git_repo["head"]
    assert review["obligation_map"] == []
    assert review["recommendation"] is None
    # No declaration was supplied, so §7.4's minor finding is recorded (M6.1)
    # and the verdict is honestly unable-to-determine with nothing analyzed.
    assert review["declaration"] is None
    assert [f["type"] for f in review["findings"]] == ["declaration_absent"]
    assert review["completion"]["verdict"] == "unable_to_determine"


def test_a_default_cli_run_is_seeded(git_repo, fixture_task_path, capsys, stub_model):
    """A plain `acceptance check` must carry the configured seed.

    `--seed` defaulted to None and every command passed it straight into
    RunConfig, so argparse silently overrode DEFAULT_SEED and no CLI run was
    ever seeded — the fixed-seed half of the determinism strategy was dead on
    the only path a user invokes. The previous version of this test asserted
    `seed is None`, which locked the defect in (#160).
    """
    exit_code = main(
        ["check", "--json", "--task", fixture_task_path, "--base", git_repo["base"], "--head", git_repo["head"]]
    )

    assert exit_code == 0
    review = json.loads(capsys.readouterr().out)
    assert review["provenance"]["controls_requested"] == {"temperature": 0.0, "seed": DEFAULT_SEED}
    # What actually held. The stub has no provider to discard anything, so the
    # two agree here; against a real provider they need not.
    assert review["provenance"]["controls_in_force"] == {"temperature": 0.0, "seed": DEFAULT_SEED}


def test_no_seed_is_the_deliberate_way_to_run_unpinned(git_repo, fixture_task_path, capsys, stub_model):
    """Seeding by default must still leave a way out: M-B0.4 samples a provider
    repeatedly to disclose variance, which a fixed seed would suppress."""
    exit_code = main(
        [
            "check", "--json", "--task", fixture_task_path,
            "--base", git_repo["base"], "--head", git_repo["head"], "--no-seed",
        ]
    )

    assert exit_code == 0
    provenance = json.loads(capsys.readouterr().out)["provenance"]
    assert provenance["controls_requested"]["seed"] is None
    # Nothing was asked for, so nothing was dropped: the run is honestly pinned
    # on temperature and simply unseeded.
    assert provenance["controls_in_force"]["seed"] is None


def test_check_records_determinism_flags_in_provenance(git_repo, fixture_task_path, capsys, stub_model):
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
        "controls_requested": {"temperature": 0.4, "seed": 7},
        "controls_in_force": {"temperature": 0.4, "seed": 7},
        # This fixture's diff surfaces no candidate tests, so the mapping stage
        # makes no call and there is no partitioning to report. None here is
        # "unpartitioned run", not "partition of size zero".
        "request_partition_size": None,
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


def test_two_runs_over_the_same_input_are_byte_identical(git_repo, fixture_task_path, capsys, stub_model):
    args = [
        "check", "--task", fixture_task_path, "--base", git_repo["base"], "--head", git_repo["head"]
    ]

    assert main(args) == 0
    first = capsys.readouterr().out
    assert main(args) == 0
    second = capsys.readouterr().out

    assert first == second


def test_report_shell_renders_all_sections_present_and_empty(git_repo, fixture_task_path, capsys, stub_model):
    exit_code = main(
        ["check", "--task", fixture_task_path, "--base", git_repo["base"], "--head", git_repo["head"]]
    )

    assert exit_code == 0
    out = capsys.readouterr().out
    # Every §16 section present...
    assert "Task completion: UNABLE-TO-DETERMINE" in out  # the real M7.2 verdict
    assert "Obligations:" in out
    assert "Unrequested changes:" in out
    assert "Recommended next instruction: (none)" in out
    # ...and empty when the checker finds nothing.
    assert out.count("(none)") == 3  # 2 list sections + the next-instruction line


def test_check_persists_the_review_to_the_store(git_repo, fixture_task_path, stub_model):
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
        client=client_finding_nothing(),
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


# --- task-file auto-ignore (a change must never appear in its own diff) ---


def test_task_ignore_pattern_for_a_file_inside_the_repo(git_repo):
    from acceptance.cli import _task_ignore_pattern

    task_path = git_repo["path"] / "current-task.md"
    task_path.write_text("# Task\n")

    pattern = _task_ignore_pattern(str(task_path), git_repo["path"])
    assert pattern == "/current-task.md"


def test_task_ignore_pattern_for_a_relative_path(git_repo, monkeypatch):
    from acceptance.cli import _task_ignore_pattern

    (git_repo["path"] / "current-task.md").write_text("# Task\n")
    monkeypatch.chdir(git_repo["path"])

    assert _task_ignore_pattern("current-task.md", git_repo["path"]) == "/current-task.md"


def test_task_ignore_pattern_is_none_outside_the_repo(git_repo, tmp_path):
    from acceptance.cli import _task_ignore_pattern

    outside = tmp_path / "elsewhere" / "task.md"
    outside.parent.mkdir()
    outside.write_text("# Task\n")

    assert _task_ignore_pattern(str(outside), git_repo["path"]) is None


def test_run_classify_auto_ignores_the_task_file(git_repo, monkeypatch):
    """The --task file must never appear in its own diff — not as a
    coverage claim, and never as an absurd "unrequested change" (it always
    changes). Verified by capturing the ignore pattern actually passed to
    change-set extraction; the capability calls themselves are stubbed out
    since their real behavior is tested elsewhere and would otherwise need
    a live model call."""
    import acceptance.cli as cli_module
    from acceptance.requirement.obligations import Decomposition

    task_path = git_repo["path"] / "current-task.md"
    task_path.write_text("# Task\nDo the thing.\n")

    captured = {}

    def fake_extract_working_tree_change_set(repo, base, extra_ignore_patterns=None):
        captured["extra_ignore_patterns"] = extra_ignore_patterns
        from acceptance.review_state import ChangeSet
        return ChangeSet(base_revision=base, head_revision="<working-tree>")

    monkeypatch.setattr(
        cli_module, "extract_working_tree_change_set", fake_extract_working_tree_change_set
    )
    monkeypatch.setattr(
        cli_module, "decompose", lambda parsed, client: Decomposition(obligations=[])
    )
    monkeypatch.setattr(cli_module, "classify_coverage", lambda obligations, cs, client: [])
    monkeypatch.setattr(
        cli_module, "detect_unrequested_changes", lambda obligations, cs, client: []
    )
    monkeypatch.setattr(
        cli_module,
        "classify_dispositions",
        lambda changes, obligations, coverages, cs, policy, client: [],
    )

    cli_module.run_classify(
        str(task_path), git_repo["base"], None, RunConfig(), repo=str(git_repo["path"])
    )

    assert captured["extra_ignore_patterns"] == ["/current-task.md"]


def test_render_classify_output():
    from acceptance.cli import render_classify
    from acceptance.coverage.classify import CoverageStatus, DiffRef, ImplementationCoverage
    from acceptance.coverage.disposition import DispositionedChange
    from acceptance.coverage.unrequested import UnrequestedChange, UnrequestedChangeKind
    from acceptance.review_state import (
        Link,
        Obligation,
        ObligationType,
        OpenQuestion,
        UnrequestedChangeDisposition,
    )

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
    dispositioned = [
        DispositionedChange(
            change=UnrequestedChange(
                kind=UnrequestedChangeKind.PUBLIC_INTERFACE,
                rationale="checkout signature changed",
                diff_refs=[DiffRef(file="cart.py", hunk_header="@@ -1 +1 @@")],
            ),
            disposition=UnrequestedChangeDisposition.RISKY,
            rationale="edits an existing public signature",
            recommendation="Scrutinize: this could hide a regression.",
        )
    ]

    open_questions = [
        OpenQuestion(id="q-1", question="Minus sign or parentheses?"),
        OpenQuestion(
            id="q-2", question="Should the total be tax-inclusive?",
            resolved=True, resolution_rationale="The diff always adds tax after the subtotal.",
            resolution_refs=[Link(kind="code", ref="pkg.py#@@ -1 +1 @@")],
        ),
    ]

    rendered = render_classify(obligations, open_questions, coverages, dispositioned)
    assert "Open questions" in rendered
    assert "[open] q-1: Minus sign or parentheses?" in rendered
    assert "[resolved] q-2: Should the total be tax-inclusive?" in rendered
    assert "answer: The diff always adds tax after the subtotal." in rendered
    assert "pkg.py#@@ -1 +1 @@" in rendered
    assert "[addressed] ob-1: Do the thing." in rendered
    assert "pkg.py" in rendered
    assert "[not_addressed] ob-2: Handle the edge." in rendered
    assert "no corresponding change" in rendered
    assert "Unrequested changes" in rendered
    # Each unrequested change now leads with its disposition, keeps its kind,
    # and carries any recommendation.
    assert "[risky] (public_interface) checkout signature changed" in rendered
    assert "cart.py" in rendered
    assert "Scrutinize" in rendered


def test_render_classify_shows_none_for_no_open_questions():
    from acceptance.cli import render_classify

    rendered = render_classify([], [], [], [])
    assert "Open questions" in rendered
    assert "(none)" in rendered


# --- ignore patterns (#105) ---


def test_render_change_set_shows_ignored_paths():
    from acceptance.cli import render_change_set
    from acceptance.review_state import ChangeSet, FileChange

    change_set = ChangeSet(
        base_revision="abc123",
        head_revision="def456",
        files=[FileChange(path="pkg.py", status="modified", category="source")],
        ignored_paths=["vendor/lib.py"],
    )

    rendered = render_change_set(change_set)
    assert "pkg.py" in rendered
    assert "Ignored by .acceptance/ignore (1):" in rendered
    assert "vendor/lib.py" in rendered


def test_render_change_set_omits_ignored_section_when_empty():
    from acceptance.cli import render_change_set
    from acceptance.review_state import ChangeSet, FileChange

    change_set = ChangeSet(
        base_revision="abc123",
        head_revision="def456",
        files=[FileChange(path="pkg.py", status="modified", category="source")],
    )

    rendered = render_change_set(change_set)
    assert "Ignored" not in rendered



# --- check: the M7.4 additions (optional declaration + working-tree review) ---


def test_check_threads_an_optional_declaration_into_the_review(
    git_repo, fixture_task_path, tmp_path, capsys, stub_model
):
    """--declaration must actually reach the pipeline: with one supplied, the
    declaration is parsed onto the Review and §7.4's "absent" minor finding is
    NOT raised. Guards a flag that parses but silently drops its value."""
    declaration = tmp_path / "declaration.md"
    declaration.write_text(
        "# Builder Declaration\n## Mandate as understood\nAdd the thing.\n"
    )

    assert main([
        "check", "--json", "--task", fixture_task_path,
        "--base", git_repo["base"], "--head", git_repo["head"],
        "--declaration", str(declaration),
    ]) == 0

    with_declaration = json.loads(capsys.readouterr().out)
    assert with_declaration["declaration"] is not None
    assert with_declaration["declaration"]["mandate_as_understood"] == "Add the thing."
    assert "declaration_absent" not in {f["type"] for f in with_declaration["findings"]}

    # ...and the same invocation WITHOUT it succeeds too, differing only in the
    # §7.4 absent finding. Pairing both runs in one test means a --declaration
    # that parses but is ignored cannot pass: the two outputs would be identical.
    assert main([
        "check", "--json", "--task", fixture_task_path,
        "--base", git_repo["base"], "--head", git_repo["head"],
    ]) == 0
    without = json.loads(capsys.readouterr().out)
    assert without["declaration"] is None
    assert "declaration_absent" in {f["type"] for f in without["findings"]}


def test_check_without_a_head_reviews_the_working_tree(
    git_repo, fixture_task_path, capsys, stub_model
):
    """Omitting --head reviews the working tree (§5.1), so a check can run
    before a commit exists. The uncommitted file must appear in the change set
    — a fixture whose tree matched HEAD would pass either way."""
    (git_repo["path"] / "uncommitted.py").write_text("def added_after_head():\n    return 1\n")

    assert main([
        "check", "--json", "--task", fixture_task_path, "--base", git_repo["base"],
    ]) == 0

    review = json.loads(capsys.readouterr().out)
    assert review["reviewed_revision"] == "<working-tree>"
    changed = {f["path"] for f in review["change_set"]["files"]}
    assert "uncommitted.py" in changed  # the working tree, not the HEAD commit


# --- M7.3: the next-instruction file ---


def test_check_writes_a_next_instruction_file_and_points_the_report_at_it(
    git_repo, fixture_task_path, capsys, monkeypatch
):
    """§10.1 step 12: when the review has gaps, `check` writes
    .acceptance/next-instruction.md and the §16 report points at it instead of
    printing "(none)"."""
    from acceptance.config import RunConfig
    from tests.support import client_dispatching

    # A checker that finds one obligation, leaves it uncovered, and recommends
    # a discriminating test for it — i.e. a review with real gaps.
    monkeypatch.setattr(RunConfig, "build_client", lambda self, completion_fn=None: client_dispatching({
        "_Decomposition": {"obligations": [{
            "id": "gap-ob", "description": "Handle the empty case",
            "type": "functional", "importance": "critical", "explicit": True,
            "observable_behavior": "...", "source_quote": "Do the thing.",
        }], "open_questions": []},
        "_Mappings": {"mappings": []},
        "_Discrimination": {"discriminations": []},
        "_Coverage": {"classifications": [{
            "obligation_id": "gap-ob", "status": "not_addressed",
            "rationale": "no code handles the empty case", "diff_refs": [],
        }]},
        "_Detections": {"unrequested_changes": []},
        "_Judgments": {"resolutions": []},
        "_Recommendations": {"recommendations": [{
            "obligation_id": "gap-ob",
            "required_inputs": "an empty collection",
            "boundary_conditions": "zero elements",
            "expected_output": "an empty result, not an error",
            "required_assertions": ["assert handle([]) == []"],
            "plausible_defect": "raises IndexError on an empty input",
            "repo_conventions": "tests/test_thing.py",
        }]},
        "_Mismatches": {"mismatches": []},
    }))

    assert main([
        "check", "--task", fixture_task_path,
        "--base", git_repo["base"], "--head", git_repo["head"],
    ]) == 0

    instruction_file = git_repo["path"] / ".acceptance" / "next-instruction.md"
    assert instruction_file.is_file()
    written = instruction_file.read_text()
    assert "Handle the empty case" in written  # the gap
    assert "Must fail if: raises IndexError on an empty input" in written  # its test
    assert "Update the builder declaration after the changes." in written
    # The §16 report's pointer now names the file rather than "(none)".
    out = capsys.readouterr().out
    assert ".acceptance/next-instruction.md" in out


def test_check_writes_no_instruction_file_when_nothing_is_wrong(
    git_repo, fixture_task_path, capsys, stub_model
):
    """A checker that finds nothing has nothing to instruct, so no file is
    written and the report still reads "(none)"."""
    assert main([
        "check", "--task", fixture_task_path,
        "--base", git_repo["base"], "--head", git_repo["head"],
    ]) == 0

    assert not (git_repo["path"] / ".acceptance" / "next-instruction.md").exists()
    assert "Recommended next instruction: (none)" in capsys.readouterr().out
