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


# --- M7.3.r1 (#167): on-demand recommendation retrieval, no pushed file ---


def _gap_client():
    """A checker that finds one uncovered obligation and recommends a test for
    it — i.e. a review with real gaps, and so a real recommendation to pull."""
    from tests.support import client_dispatching

    return client_dispatching({
        "_Decomposition": {"obligations": [{
            "id": "gap-ob", "description": "Handle the empty case",
            "type": "functional", "importance": "critical", "explicit": True,
            "observable_behavior": "...", "source_quote": "Do the thing.",
        }], "open_questions": [], "requirement_dispositions": []},
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
            "repo_conventions": "follow the fixtures in tests/test_thing.py",
        }]},
        "_Mismatches": {"mismatches": []},
    })


def _run_check_with_gaps(git_repo, fixture_task_path, monkeypatch):
    from acceptance.config import RunConfig

    monkeypatch.setattr(
        RunConfig, "build_client", lambda self, completion_fn=None: _gap_client()
    )
    assert main([
        "check", "--task", fixture_task_path,
        "--base", git_repo["base"], "--head", git_repo["head"],
    ]) == 0


def test_check_writes_no_instruction_file_even_when_the_review_has_gaps(
    git_repo, fixture_task_path, capsys, monkeypatch
):
    """The push is gone. This is exactly the case that used to write the file."""
    _run_check_with_gaps(git_repo, fixture_task_path, monkeypatch)

    assert not (git_repo["path"] / ".acceptance" / "next-instruction.md").exists()
    out = capsys.readouterr().out
    assert "acceptance recommendation --criterion gap-ob" in out
    assert "next-instruction.md" not in out


def test_a_stale_instruction_file_is_removed_and_the_removal_reported(
    git_repo, fixture_task_path, capsys, stub_model
):
    """The case the old `test_cli.py:565` missed, and the point of the migration.

    That test asserted the file was absent after a clean run, but passed only
    because the fixture repo was fresh — it never had one. Here the repo ALREADY
    contains a stale file, which is the state every repo that ran the previous
    version is in. Left alone it keeps asserting gaps that no longer exist,
    contradicting a clean report; both cannot be true and only the report is
    entitled to speak.
    """
    stale = git_repo["path"] / ".acceptance" / "next-instruction.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("# Next instruction\n\nSomething that is no longer true.\n")

    assert main([
        "check", "--task", fixture_task_path,
        "--base", git_repo["base"], "--head", git_repo["head"],
    ]) == 0

    assert not stale.exists()
    # Visible, not silent — it touched a file in the user's repo. On stderr so
    # the notice appears in every output mode, `--json` included.
    assert "Removed a stale" in capsys.readouterr().err


def test_the_removal_leaves_the_report_as_the_only_statement_of_status(
    git_repo, fixture_task_path, capsys, stub_model
):
    """A clean run starting from a repo that already contains the file: nothing
    is left on disk to contradict the report."""
    stale = git_repo["path"] / ".acceptance" / "next-instruction.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("# Next instruction\n\nStale gaps.\n")

    assert main([
        "check", "--task", fixture_task_path,
        "--base", git_repo["base"], "--head", git_repo["head"],
    ]) == 0

    assert not stale.exists()
    assert "Recommended next instruction: (none)" in capsys.readouterr().out


def test_recommendation_returns_the_stored_prescription_for_a_criterion(
    git_repo, fixture_task_path, capsys, monkeypatch
):
    """Retrieval reads review state — no re-run, no model call."""
    import json

    _run_check_with_gaps(git_repo, fixture_task_path, monkeypatch)
    capsys.readouterr()

    assert main(["recommendation", "--criterion", "gap-ob"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["obligation_id"] == "gap-ob"
    # Every §9.5 field, each holding its prose rather than a flattened token —
    # the reasoning inside them is what makes a recommendation actionable, and a
    # regression that compressed only the unasserted ones would otherwise pass.
    assert payload["required_inputs"] == "an empty collection"
    assert payload["boundary_conditions"] == "zero elements"
    assert payload["expected_output"] == "an empty result, not an error"
    assert payload["required_assertions"] == ["assert handle([]) == []"]
    assert payload["plausible_defect"] == "raises IndexError on an empty input"
    assert payload["repo_conventions"] == "follow the fixtures in tests/test_thing.py"
    # Prose, not codes: multi-word text survives the round trip.
    assert all(
        len(str(payload[field]).split()) > 1
        for field in (
            "required_inputs", "boundary_conditions", "expected_output",
            "plausible_defect", "repo_conventions",
        )
    )


def test_recommendation_for_an_unknown_criterion_is_empty_not_an_error(
    git_repo, fixture_task_path, capsys, monkeypatch
):
    """A strongly-supported obligation earns no recommendation, and asking about
    one is a reasonable thing for an agent to do."""
    _run_check_with_gaps(git_repo, fixture_task_path, monkeypatch)
    capsys.readouterr()

    assert main(["recommendation", "--criterion", "no-such-obligation"]) == 0
    assert capsys.readouterr().out.strip() == "{}"


def test_two_retrievals_over_unchanged_state_are_byte_identical(
    git_repo, fixture_task_path, capsys, monkeypatch
):
    _run_check_with_gaps(git_repo, fixture_task_path, monkeypatch)
    capsys.readouterr()

    assert main(["recommendation", "--criterion", "gap-ob"]) == 0
    first = capsys.readouterr().out
    assert main(["recommendation", "--criterion", "gap-ob"]) == 0
    second = capsys.readouterr().out

    assert first == second


def _store_review_with(tmp_path, revision, criterion, defect):
    """Write a review straight into the store, so a test can control what is
    stored and in what order without running a review to get it there."""
    from acceptance.review_state import Review, TestRecommendation
    from acceptance.review_store import ReviewStore

    review = Review(
        mode="local",
        reviewed_revision=revision,
        recommendations=[
            TestRecommendation(
                obligation_id=criterion,
                criterion="A criterion",
                required_inputs="inputs",
                boundary_conditions="edges",
                expected_output="output",
                required_assertions=["assert True"],
                plausible_defect=defect,
                repo_conventions="conventions",
            )
        ],
    )
    return ReviewStore(tmp_path / ".acceptance" / "cache" / "reviews").write(review)


def test_retrieval_reads_the_named_revision_and_not_a_recomputation(
    monkeypatch, tmp_path, capsys
):
    """Two stored reviews disagree about the same criterion, so reading the
    wrong one — or recomputing instead of reading — is observable.

    The previous version of this test stored a single review, which cannot
    distinguish "read the stored state" from "recomputed and happened to agree".
    """
    import json

    monkeypatch.chdir(tmp_path)
    _store_review_with(tmp_path, "a" * 40, "ob-1", "the OLDER defect")
    _store_review_with(tmp_path, "b" * 40, "ob-1", "the NEWER defect")

    assert main(["recommendation", "--criterion", "ob-1", "--revision", "a" * 40]) == 0
    assert json.loads(capsys.readouterr().out)["plausible_defect"] == "the OLDER defect"

    assert main(["recommendation", "--criterion", "ob-1", "--revision", "b" * 40]) == 0
    assert json.loads(capsys.readouterr().out)["plausible_defect"] == "the NEWER defect"


def test_retrieval_makes_no_model_call(monkeypatch, tmp_path, capsys):
    """Retrieval reads state; it never re-runs the review. That is the whole
    reason the pull is cheap, so it is asserted rather than assumed."""
    from acceptance import cli
    from acceptance.config import RunConfig

    monkeypatch.chdir(tmp_path)
    _store_review_with(tmp_path, "a" * 40, "ob-1", "a defect")

    def explode(self, completion_fn=None):
        raise AssertionError("retrieval built a model client")

    monkeypatch.setattr(RunConfig, "build_client", explode)
    monkeypatch.setattr(
        cli, "run_review", lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("retrieval re-ran the review pipeline")
        )
    )

    assert main(["recommendation", "--criterion", "ob-1"]) == 0
    assert "a defect" in capsys.readouterr().out


def test_retrieval_without_a_revision_uses_the_newest_stored_review(
    monkeypatch, tmp_path, capsys
):
    """Oldest-vs-newest has to be observable, so the store holds two reviews
    that disagree, written in a known order."""
    import json
    import os

    monkeypatch.chdir(tmp_path)
    older = _store_review_with(tmp_path, "a" * 40, "ob-1", "the OLDER defect")
    newer = _store_review_with(tmp_path, "b" * 40, "ob-1", "the NEWER defect")
    # Pin write order explicitly rather than trusting filesystem timestamp
    # resolution, which is coarse enough on some platforms to make two writes
    # in the same test look simultaneous.
    os.utime(older, (1_000_000, 1_000_000))
    os.utime(newer, (2_000_000, 2_000_000))

    assert main(["recommendation", "--criterion", "ob-1"]) == 0

    assert json.loads(capsys.readouterr().out)["plausible_defect"] == "the NEWER defect"


def test_the_newest_review_wins_regardless_of_filename_order(
    monkeypatch, tmp_path, capsys
):
    """Reviews are keyed by revision, and revisions carry no order. A store that
    sorted by name would pass the test above by accident, so here the newest
    review is the alphabetically FIRST filename."""
    import json
    import os

    monkeypatch.chdir(tmp_path)
    older = _store_review_with(tmp_path, "z" * 40, "ob-1", "the OLDER defect")
    newer = _store_review_with(tmp_path, "a" * 40, "ob-1", "the NEWER defect")
    os.utime(older, (1_000_000, 1_000_000))
    os.utime(newer, (2_000_000, 2_000_000))

    assert main(["recommendation", "--criterion", "ob-1"]) == 0

    assert json.loads(capsys.readouterr().out)["plausible_defect"] == "the NEWER defect"


def test_recommendation_without_a_stored_review_fails_cleanly(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)

    assert main(["recommendation", "--criterion", "anything"]) == 1
    assert "no stored review" in capsys.readouterr().err


def test_json_is_the_default_format_when_none_is_requested(
    git_repo, fixture_task_path, capsys, monkeypatch
):
    """JSON by default because the consumer is a coding agent, not a human.

    Asserted by name rather than left implicit in a test that happens to
    `json.loads` the output: a change of default is the kind of thing that
    slips through when nothing states the guarantee.
    """
    import json

    _run_check_with_gaps(git_repo, fixture_task_path, monkeypatch)
    capsys.readouterr()

    assert main(["recommendation", "--criterion", "gap-ob"]) == 0
    default = capsys.readouterr().out

    assert main(["recommendation", "--criterion", "gap-ob", "--format", "json"]) == 0
    explicit = capsys.readouterr().out

    assert default == explicit
    assert json.loads(default)["obligation_id"] == "gap-ob"


# --- the command surface the spec names must be the one the CLI accepts ------
#
# #167 fixed the surface up front precisely so §16 could name a specific
# command. A doc written against a command that later changes would recreate the
# two-artifacts-drifting failure the whole task exists to remove — so the spec
# string and the parser are pinned to each other here.

_DOCUMENTED_COMMAND = "acceptance recommendation --criterion <id>"


def _spec_text():
    from pathlib import Path

    spec = Path(__file__).resolve().parents[1] / "docs" / (
        "AI-Assisted-Software-Development-Review-Spec.md"
    )
    return spec.read_text()


def test_the_spec_names_the_command_the_cli_actually_accepts():
    from acceptance.cli import build_parser

    assert _DOCUMENTED_COMMAND in _spec_text()

    _, _, flags = _DOCUMENTED_COMMAND.partition("acceptance ")
    command, criterion_flag, _ = flags.split()
    args = build_parser().parse_args([command, criterion_flag, "some-id"])

    assert args.command == "recommendation"
    assert args.criterion == "some-id"
    assert args.format == "json"


def test_the_spec_no_longer_names_a_written_file():
    assert "next-instruction.md" not in _spec_text()


def test_a_command_name_the_spec_does_not_document_is_rejected(capsys):
    import pytest

    for wrong in ("recommend", "recommendations"):
        with pytest.raises(SystemExit):
            build_parser_parse([wrong, "--criterion", "x"])


def test_criterion_is_required(capsys):
    import pytest

    with pytest.raises(SystemExit):
        build_parser_parse(["recommendation"])


def test_an_undocumented_format_is_rejected(capsys):
    import pytest

    with pytest.raises(SystemExit):
        build_parser_parse(["recommendation", "--criterion", "x", "--format", "yaml"])


def build_parser_parse(argv):
    from acceptance.cli import build_parser

    return build_parser().parse_args(argv)


def test_the_removal_is_reported_in_json_mode_too(
    git_repo, fixture_task_path, capsys, stub_model
):
    """Deleting a file in the user's repo must never be silent, in any mode.

    The first version printed the notice only on the text branch, so `--json`
    deleted the file and said nothing — found by the tool's own Gate 2 run. The
    notice goes to stderr so stdout stays parseable for the agent.
    """
    import json

    stale = git_repo["path"] / ".acceptance" / "next-instruction.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("# Next instruction\n\nStale.\n")

    assert main([
        "check", "--task", fixture_task_path,
        "--base", git_repo["base"], "--head", git_repo["head"], "--json",
    ]) == 0

    captured = capsys.readouterr()
    assert not stale.exists()
    assert "Removed a stale" in captured.err
    json.loads(captured.out)  # stdout is still pure JSON


def test_retrieval_writes_nothing_into_the_repo(monkeypatch, tmp_path, capsys):
    """`no-speculative-writing` covers retrieval, not just `check`.

    Nothing is written speculatively, so nothing can go stale — the premise of
    the whole pull model. Snapshotting the tree around the command is the only
    way to assert it; proving no model call happens is a weaker claim.
    """
    monkeypatch.chdir(tmp_path)
    _store_review_with(tmp_path, "a" * 40, "ob-1", "a defect")

    def snapshot():
        return {p.relative_to(tmp_path): p.stat().st_mtime for p in tmp_path.rglob("*")}

    before = snapshot()
    assert main(["recommendation", "--criterion", "ob-1"]) == 0
    capsys.readouterr()

    assert snapshot() == before


def test_the_spec_does_not_frame_the_recommendation_as_a_written_artifact():
    """Stronger than asserting the old filename is gone.

    The spec kept "the recommendation may surface in ... a Markdown file" long
    after `next-instruction.md` was removed from it, so a filename check passed
    while the file-writing framing survived — found by the tool's own Gate 2 run.
    """
    spec = _spec_text()

    assert "Markdown file" not in spec
    assert "acceptance recommendation --criterion <id>" in spec
    # The §10.1 step-12 wording that replaced the pushed artifact.
    assert "never pushed to a file that outlives the run that wrote it" in spec


def test_the_pipeline_persists_the_requirement_map(git_repo, tmp_path, stub_model):
    """Wiring, not the function (CLAUDE.md).

    `decompose` building a mapping is worth nothing if `run_review` drops it on
    the floor — the shape of hole defect injection keeps finding here. The stub
    client accounts for no requirement at all, so every one of them must come
    back `undisposed`: a review that persisted an empty or absent map would be
    indistinguishable from one whose decomposer read the whole mandate, which is
    the exact defect M1.2.r1 exists to close.
    """
    task = tmp_path / "task.md"
    task.write_text(
        "# Task\nRender each invoice line.\n\n"
        "## Constraints\n- Format money as USD.\n- Keep the CSV export unchanged.\n\n"
        "## Scope exclusions\n- Changing the PDF renderer.\n"
    )

    assert main(
        ["check", "--task", str(task), "--base", git_repo["base"], "--head", git_repo["head"]]
    ) == 0

    stored = ReviewStore().read(git_repo["head"])
    assert stored.requirement_map is not None
    assert [r.id for r in stored.requirement_map.requirements] == [
        "task",
        "constraint-01",
        "constraint-02",
        "exclusion-01",
    ]
    assert len(stored.requirement_map.undisposed()) == 4


def test_a_requirement_that_yielded_nothing_is_visible_in_the_report(
    git_repo, tmp_path, capsys, stub_model
):
    """DR-202's "present in the mapping with a reason, and visible in the
    rendered report — not absent from it". Rendering the empty case IS the
    deliverable: previously a requirement that produced no obligation simply did
    not appear, so the reader was told nothing was missing because there was
    nothing there to say it."""
    task = tmp_path / "task.md"
    task.write_text("# Task\nRender each invoice line.\n\n## Constraints\n- Format money as USD.\n")

    assert main(
        ["check", "--task", str(task), "--base", git_repo["base"], "--head", git_repo["head"]]
    ) == 0

    report = capsys.readouterr().out
    assert "Mandate coverage: 0 of 2 requirements yielded obligations" in report
    assert "constraint-01" in report
    assert "Format money as USD." in report
