"""Incremental re-run against a new head (M7.5, §13.5 #9)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from acceptance.rerun import (
    carried_findings,
    carried_recommendations,
    compute_delta,
    find_prior_review,
    merge_carried_forward,
    obligations_to_rederive,
    stale_obligation_ids,
    task_source_for,
)
from acceptance.review_state import (
    ChangeSet,
    Component,
    EvidenceTier,
    FileChange,
    Finding,
    Link,
    Obligation,
    ObligationType,
    Review,
    TestRecommendation,
)
from acceptance.review_store import ReviewStore

TASK = "# Task\nRound half to even.\n"


def _obligation(
    obligation_id: str,
    *,
    description: str | None = None,
    coverage_refs: list[str] | None = None,
    test_evidence: list[str] | None = None,
    coverage_status: str | None = "addressed",
    evidence_class: str | None = "strongly_supported",
    carried_forward_from: str | None = None,
) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=description or f"obligation {obligation_id}",
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="...",
        coverage_refs=coverage_refs or [],
        test_evidence=test_evidence or [],
        coverage_status=coverage_status,
        evidence_class=evidence_class,
        achieved_evidence_tier=EvidenceTier.STATIC,
        carried_forward_from=carried_forward_from,
    )


def _review(revision: str, obligations: list[Obligation], **extra) -> Review:
    return Review(
        mode="local",
        reviewed_revision=revision,
        task_source=task_source_for(TASK, "task.md"),
        obligation_map=obligations,
        **extra,
    )


def _change_set(*paths: str) -> ChangeSet:
    return ChangeSet(
        base_revision="base",
        head_revision="head",
        files=[FileChange(path=path, status="modified", category="source") for path in paths],
    )


# --- which obligations must be re-derived ----------------------------------


def test_an_obligation_whose_files_are_untouched_is_not_re_derived():
    prior = _review("old", [_obligation("a", coverage_refs=["rounding.py#@@ -1 +1 @@"])])

    stale = stale_obligation_ids(prior, _change_set("unrelated.py"))

    assert stale == set()


def test_an_obligation_whose_code_changed_is_re_derived():
    prior = _review("old", [_obligation("a", coverage_refs=["rounding.py#@@ -1 +1 @@"])])

    assert stale_obligation_ids(prior, _change_set("rounding.py")) == {"a"}


def test_an_obligation_whose_test_changed_is_re_derived():
    """Its code may be untouched while the evidence about it moved.

    The code citation is deliberately present and untouched: without it the
    obligation would be stale merely for having no citations at all, and this
    test would pass whether or not test files are consulted (it did, until a
    defect injection showed it could not fail).
    """
    prior = _review(
        "old",
        [
            _obligation(
                "a",
                coverage_refs=["rounding.py#@@ -1 +1 @@"],
                test_evidence=["test_rounding.py::test_ties"],
            )
        ],
    )

    assert stale_obligation_ids(prior, _change_set("test_rounding.py")) == {"a"}


def test_an_obligation_with_no_citations_is_always_re_derived():
    """Nothing proves the new work missed it, so it cannot be assumed unaffected."""
    prior = _review(
        "old", [_obligation("a", coverage_status="not_addressed", evidence_class="unsupported")]
    )

    assert stale_obligation_ids(prior, _change_set("anything.py")) == {"a"}


def test_a_renamed_files_old_path_also_invalidates():
    """An obligation citing the pre-rename path is affected by the rename."""
    prior = _review("old", [_obligation("a", coverage_refs=["old_name.py#@@ -1 +1 @@"])])
    change_set = ChangeSet(
        base_revision="base",
        head_revision="head",
        files=[
            FileChange(
                path="new_name.py", old_path="old_name.py", status="renamed", category="source"
            )
        ],
    )

    assert stale_obligation_ids(prior, change_set) == {"a"}


def test_an_obligation_the_prior_review_never_saw_is_re_derived():
    prior = _review("old", [_obligation("a", coverage_refs=["a.py#@@ -1 +1 @@"])])
    fresh = [_obligation("a"), _obligation("b")]

    targets = obligations_to_rederive(fresh, prior, _change_set("unrelated.py"))

    assert [o.id for o in targets] == ["b"]


# --- carrying judgments forward --------------------------------------------


def test_a_carried_forward_judgment_names_the_revision_it_was_established_at():
    """A carried judgment is evidence about an OLDER head; the report has to be
    able to say which one, or it presents stale evidence as current."""
    prior = _review("abc123", [_obligation("a", evidence_class="unsupported")])

    merged = merge_carried_forward([_obligation("a")], judged=[], prior=prior)

    assert merged[0].carried_forward_from == "abc123"
    assert merged[0].evidence_class == "unsupported"  # the prior judgment, not the fresh default


def test_carrying_a_carried_judgment_forward_again_keeps_the_original_revision():
    """Otherwise the label drifts to the last run that reused the judgment, and a
    judgment established five heads ago would claim to be one head old."""
    prior = _review("second", [_obligation("a", carried_forward_from="first")])

    merged = merge_carried_forward([_obligation("a")], judged=[], prior=prior)

    assert merged[0].carried_forward_from == "first"


def test_a_re_derived_obligation_is_not_marked_carried_forward():
    prior = _review("abc123", [_obligation("a", evidence_class="unsupported")])
    judged = [_obligation("a", evidence_class="strongly_supported")]

    merged = merge_carried_forward([_obligation("a")], judged=judged, prior=prior)

    assert merged[0].carried_forward_from is None
    assert merged[0].evidence_class == "strongly_supported"


def test_a_prior_gap_finding_survives_a_rerun_that_did_not_re_examine_it():
    """The verdict reads gaps off findings, so dropping the finding for an
    obligation nobody touched would report an open gap as resolved — the re-run
    would launder a gap by not looking at it."""
    gap = Finding(
        type="coverage_gap",
        severity="high",
        description="ties not handled",
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="requirement", ref="task.md:1")],
        related_obligation="obligation a",
    )
    prior = _review("old", [_obligation("a")], findings=[gap])
    carried = [_obligation("a", carried_forward_from="old")]

    assert carried_findings(prior, carried) == [gap]


def test_a_prior_recommendation_survives_for_a_carried_obligation():
    """Otherwise the agent loses the instruction for a gap that is still open."""
    recommendation = TestRecommendation(
        obligation_id="a",
        criterion="ties go to even",
        required_inputs="2.5, 3.5",
        boundary_conditions="exact .5",
        expected_output="2 and 4",
        plausible_defect="round-half-up",
        repo_conventions="pytest, tests/ mirrors src/",
    )
    prior = _review("old", [_obligation("a")], recommendations=[recommendation])

    assert carried_recommendations(prior, [_obligation("a", carried_forward_from="old")]) == [
        recommendation
    ]


# --- the delta --------------------------------------------------------------


def test_the_delta_reports_a_closed_gap():
    prior = _review(
        "old",
        [_obligation("a", coverage_status="not_addressed", evidence_class="unsupported")],
    )
    current = [_obligation("a", coverage_status="addressed", evidence_class="strongly_supported")]

    delta = compute_delta(prior, current, verdict="no_material_gaps")

    assert [change.obligation_id for change in delta.closed_gaps()] == ["a"]
    assert delta.previous_verdict is None
    assert delta.verdict == "no_material_gaps"


def test_weak_evidence_becoming_strong_counts_as_a_closed_gap():
    """Archetype 9's actual shape: the code was addressed all along, but the only
    test could not tell banker's rounding from round-half-up."""
    prior = _review("old", [_obligation("a", evidence_class="nominally_supported")])
    current = [_obligation("a", evidence_class="strongly_supported")]

    delta = compute_delta(prior, current, verdict="no_material_gaps")

    assert [change.obligation_id for change in delta.closed_gaps()] == ["a"]


def test_an_obligation_that_did_not_move_is_not_reported_as_a_change():
    prior = _review("old", [_obligation("a")])

    delta = compute_delta(prior, [_obligation("a")], verdict="no_material_gaps")

    assert delta.obligation_changes == []


def test_tests_appearing_for_a_non_code_obligation_is_not_a_closed_gap():
    """`requires_other_evidence` means code tests are the wrong instrument, so a
    test showing up does not settle it."""
    prior = _review("old", [_obligation("a", evidence_class="requires_other_evidence")])
    current = [_obligation("a", evidence_class="strongly_supported")]

    delta = compute_delta(prior, current, verdict="no_material_gaps")

    assert delta.closed_gaps() == []


def test_the_delta_lists_which_obligations_were_carried_forward():
    prior = _review("old", [_obligation("a"), _obligation("b")])
    current = [_obligation("a", carried_forward_from="old"), _obligation("b")]

    delta = compute_delta(prior, current, verdict="no_material_gaps")

    assert delta.carried_forward_obligation_ids == ["a"]


# --- finding the prior review ----------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def _repo_with_two_commits(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "rounding.py").write_text("def f():\n    return 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "first")
    first = _git(repo, "rev-parse", "HEAD")
    (repo / "rounding.py").write_text("def f():\n    return 2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "second")
    second = _git(repo, "rev-parse", "HEAD")
    return repo, first, second


def test_the_prior_review_is_an_ancestor_of_the_new_head(tmp_path):
    repo, first, second = _repo_with_two_commits(tmp_path)
    store = ReviewStore(tmp_path / "reviews")
    store.write(_review(first, [_obligation("a")]))

    prior = find_prior_review(store, second, repo, TASK)

    assert prior is not None and prior.reviewed_revision == first


def test_a_review_on_a_divergent_branch_is_not_used_as_the_prior(tmp_path):
    """Reconciling branches is out of scope; a review of a commit that is not an
    ancestor describes a different line of work and must not be merged in."""
    repo, first, second = _repo_with_two_commits(tmp_path)
    _git(repo, "checkout", "-q", "-b", "side", first)
    (repo / "other.py").write_text("x = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "side")
    sideways = _git(repo, "rev-parse", "HEAD")
    store = ReviewStore(tmp_path / "reviews")
    store.write(_review(sideways, [_obligation("a")]))

    assert find_prior_review(store, second, repo, TASK) is None


def test_the_nearest_ancestor_wins_regardless_of_write_order(tmp_path):
    """Ordering must come from history, not from when reviews happened to be
    written: the store keeps no timestamps, deliberately, because wall-clock
    state would break byte-identical re-runs (M0.5)."""
    repo, first, second = _repo_with_two_commits(tmp_path)
    (repo / "rounding.py").write_text("def f():\n    return 3\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "third")
    third = _git(repo, "rev-parse", "HEAD")

    store = ReviewStore(tmp_path / "reviews")
    # Written oldest-last, so a recency heuristic would pick `first`.
    store.write(_review(second, [_obligation("nearest")]))
    store.write(_review(first, [_obligation("further")]))

    prior = find_prior_review(store, third, repo, TASK)

    assert prior is not None and prior.reviewed_revision == second


def test_a_prior_review_of_a_different_task_is_not_used(tmp_path):
    """Obligations are a function of the task text, so if the task changed the
    prior judgments are about different obligations and none can carry forward."""
    repo, first, second = _repo_with_two_commits(tmp_path)
    store = ReviewStore(tmp_path / "reviews")
    store.write(
        Review(
            mode="local",
            reviewed_revision=first,
            task_source=task_source_for("# Task\nSomething else entirely.\n", "task.md"),
            obligation_map=[_obligation("a")],
        )
    )

    assert find_prior_review(store, second, repo, TASK) is None


def test_a_review_predating_task_recording_is_not_used(tmp_path):
    """Reviews written before the task was recorded cannot be compared, so they
    are skipped rather than assumed to match."""
    repo, first, second = _repo_with_two_commits(tmp_path)
    store = ReviewStore(tmp_path / "reviews")
    store.write(Review(mode="local", reviewed_revision=first, obligation_map=[_obligation("a")]))

    assert find_prior_review(store, second, repo, TASK) is None


# --- archetype 9 end to end (the M7.5 acceptance criterion) -----------------

ARCHETYPES_DIR = Path(__file__).parent / "fixtures" / "archetypes"

# The task's own words, so decomposition's source spans resolve against it.
_NEAREST_QUOTE = "rounding to the nearest\ninteger"
_TIES_QUOTE = "ties going to the even neighbour (banker's rounding)"

_HEAD_JUDGMENTS = {
    "_Decomposition": {
        "obligations": [
            {
                "id": "round-nearest",
                "description": "Round to the nearest integer",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "round_half_even(2.3) == 2",
                "source_quote": _NEAREST_QUOTE,
            },
            {
                "id": "ties-to-even",
                "description": "Ties go to the even neighbour (banker's rounding)",
                "type": "boundary",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "round_half_even(2.5) == 2 and (3.5) == 4",
                "source_quote": _TIES_QUOTE,
            },
        ],
        "open_questions": [],
        "requirement_dispositions": [],
    },
    "_Mappings": {
        "mappings": [
            {
                "test_id": "test_rounding.py::test_rounds_to_nearest",
                "obligation_ids": ["round-nearest"],
                "rationale": "Asserts 2.3 -> 2.",
            },
            {
                "test_id": "test_rounding.py::test_ties_round_to_even",
                "obligation_ids": ["ties-to-even"],
                "rationale": "Asserts both tie directions.",
            },
        ]
    },
    "_Discrimination": {
        "obligations": [
            {
                "obligation_id": "round-nearest",
                "defects": [
                    {
                        "description": "truncates instead of rounding",
                        "would_be_caught": True,
                        "reason": "2.3 would return 2 either way, but 2.5 pins it.",
                    }
                ],
            },
            {
                "obligation_id": "ties-to-even",
                "defects": [
                    {
                        "description": "rounds half up",
                        "would_be_caught": True,
                        "reason": "2.5 -> 2 fails under round-half-up.",
                    }
                ],
            },
        ]
    },
    # The re-run reaches the pipeline through the ANCHORED schema, because the
    # prior review rated `ties-to-even` and the head touches the file holding its
    # mapped test (#292). The rating moves, so the judgement has to say what it
    # rests on — and here it genuinely rests on something: the builder added the
    # tie test this whole archetype is about. Same verdicts as `_Discrimination`
    # above, plus the justification.
    "_AnchoredDiscrimination": {
        "obligations": [
            {
                "obligation_id": "round-nearest",
                "defects": [
                    {
                        "description": "truncates instead of rounding",
                        "would_be_caught": True,
                        "reason": "2.3 would return 2 either way, but 2.5 pins it.",
                    }
                ],
                "rests_on": [],
            },
            {
                "obligation_id": "ties-to-even",
                "defects": [
                    {
                        "description": "rounds half up",
                        "would_be_caught": True,
                        "reason": "2.5 -> 2 fails under round-half-up.",
                    }
                ],
                "rests_on": ["mapped-test-file:test_rounding.py"],
            },
        ]
    },
    "_Coverage": {
        "classifications": [
            {
                "obligation_id": "round-nearest",
                "status": "addressed",
                "rationale": "Implemented in rounding.py.",
                "diff_refs": [],
            },
            {
                "obligation_id": "ties-to-even",
                "status": "addressed",
                "rationale": "The head rounds ties to even.",
                "diff_refs": [],
            },
        ]
    },
    "_Detections": {"unrequested_changes": []},
    "_Judgments": {"resolutions": []},
    "_Recommendations": {"recommendations": []},
    "_Mismatches": {"mismatches": []},
}


def test_archetype_9_rerun_flips_the_weak_obligation_and_updates_the_verdict(tmp_path):
    """§13.5 #9, the M7.5 acceptance criterion.

    The prior review is constructed rather than produced by a first pipeline run:
    it is the *input* to the re-run, and building it directly pins the base state
    exactly (ties-to-even implemented but untested — the gap archetype 9 exists to
    pose). The re-run is the real pipeline.

    Scope of the claim: this verifies the re-run MECHANISM — the flip propagates
    into the delta, the closed gap is reported, and the verdict moves. It says
    nothing about whether a real model would judge archetype 9 that way; that is
    M3/M5's accuracy, scored by the benchmark. Both obligations cite files the
    head touches, so both are re-derived here; carry-forward is covered above.
    """
    from acceptance.benchmark.fixtures import build_benchmark_case
    from acceptance.cli import run_check
    from acceptance.config import RunConfig
    from tests.support import client_dispatching

    case = build_benchmark_case(ARCHETYPES_DIR / "09-revision-cycle", tmp_path / "repo")
    repo = Path(case.inputs.repo)
    store = ReviewStore(tmp_path / "reviews")

    # What a review of the first pass concluded: the code is there, but the only
    # test cannot tell banker's rounding from round-half-up.
    store.write(
        Review(
            mode="local",
            reviewed_revision=case.inputs.base_revision,
            task_source=task_source_for(case.inputs.task_text, "task.md"),
            obligation_map=[
                _obligation(
                    "round-nearest",
                    coverage_refs=["rounding.py#@@ -0,0 +1,4 @@"],
                    test_evidence=["test_rounding.py::test_rounds_to_nearest"],
                ),
                _obligation(
                    "ties-to-even",
                    coverage_refs=["rounding.py#@@ -0,0 +1,4 @@"],
                    test_evidence=["test_rounding.py::test_rounds_to_nearest"],
                    evidence_class="nominally_supported",
                ),
            ],
            findings=[
                Finding(
                    type="coverage_gap",
                    severity="high",
                    description="No test exercises a tie, so the assertion cannot discriminate.",
                    evidence_tier=EvidenceTier.STATIC,
                    produced_by=Component.STATIC_ANALYZER,
                    links=[Link(kind="requirement", ref="task.md:1")],
                    related_obligation="Ties go to the even neighbour (banker's rounding)",
                )
            ],
        )
    )

    task_file = tmp_path / "task.md"
    task_file.write_text(case.inputs.task_text)
    review = run_check(
        task=str(task_file),
        base=case.inputs.base_revision,
        head=case.inputs.head_revision,
        config=RunConfig(),
        store=store,
        repo=repo,
        client=client_dispatching(_HEAD_JUDGMENTS),
    )

    # The prior review was found by ancestry, with no --since needed.
    assert review.delta is not None
    assert review.delta.prior_reviewed_revision == case.inputs.base_revision

    # The previously weak obligation flipped, and it is reported as a closed gap.
    ties = next(o for o in review.obligation_map if o.id == "ties-to-even")
    assert ties.evidence_class == "strongly_supported"
    assert [change.obligation_id for change in review.delta.closed_gaps()] == ["ties-to-even"]

    # And the verdict moved with it.
    assert review.delta.verdict == "no_material_gaps"
    assert review.completion is not None
    assert review.completion.verdict.value == "no_material_gaps"


# --- the re-run must not launder a gap by not looking (pipeline level) ------

_TWO_FILE_JUDGMENTS = {
    "_Decomposition": {
        "obligations": [
            {
                "id": "alpha",
                "description": "Alpha behaves",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "alpha() == 1",
                "source_quote": "Alpha behaves",
            },
            {
                "id": "beta",
                "description": "Beta behaves",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "beta() == 2",
                "source_quote": "Beta behaves",
            },
        ],
        "open_questions": [],
        "requirement_dispositions": [],
    },
    "_Mappings": {"mappings": []},
    "_Discrimination": {"obligations": []},
    "_Coverage": {
        "classifications": [
            {
                "obligation_id": "alpha",
                "status": "addressed",
                "rationale": "alpha.py implements it.",
                "diff_refs": [],
            }
        ]
    },
    "_Detections": {"unrequested_changes": []},
    "_Judgments": {"resolutions": []},
    "_Recommendations": {"recommendations": []},
    "_Mismatches": {"mismatches": []},
}

# §7.1-shaped: bullets under `# Task` are claimed by no section, so a
# file in the old shape yields an empty registry and — since #204
# partitions by requirement — no derivation call at all.
_TWO_FILE_TASK = (
    "# Task\nAlpha and beta behave.\n\n## Constraints\n- Alpha behaves\n- Beta behaves\n"
)


def test_a_rerun_still_reports_a_gap_in_code_the_new_work_never_touched(tmp_path):
    """The guarantee that makes incrementality safe rather than a loophole.

    The verdict reads gaps off findings. If a re-run drops the finding for an
    obligation it declined to re-examine, an untouched gap silently disappears
    and the review reports it as resolved — a re-run could then close every gap
    by changing an unrelated file. A defect injection that removed the
    carry-forward of prior findings survived the unit tests, which only covered
    the helper; nothing checked the pipeline actually used it.
    """
    from acceptance.change.diff import extract_change_set
    from acceptance.pipeline import run_review
    from tests.support import client_dispatching

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "alpha.py").write_text("def alpha():\n    return 1\n")
    (repo / "beta.py").write_text("def beta():\n    return 0\n")  # wrong, and untested
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "alpha.py").write_text("def alpha():\n    return 1  # tidied\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    head = _git(repo, "rev-parse", "HEAD")

    beta_gap = Finding(
        type="coverage_gap",
        severity="high",
        description="beta() returns 0, not 2.",
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="requirement", ref="task.md:1")],
        related_obligation="Beta behaves",
    )
    prior = Review(
        mode="local",
        reviewed_revision=base,
        task_source=task_source_for(_TWO_FILE_TASK, "task.md"),
        obligation_map=[
            _obligation(
                "alpha",
                description="Alpha behaves",
                coverage_refs=["alpha.py#@@ -1 +1 @@"],
            ),
            _obligation(
                "beta",
                description="Beta behaves",
                coverage_refs=["beta.py#@@ -1 +1 @@"],
                coverage_status="not_addressed",
                evidence_class="unsupported",
            ),
        ],
        findings=[beta_gap],
        recommendations=[
            TestRecommendation(
                obligation_id="beta",
                criterion="beta() returns 2",
                required_inputs="none",
                boundary_conditions="n/a",
                expected_output="2",
                plausible_defect="returns 0",
                repo_conventions="pytest",
            )
        ],
    )

    review = run_review(
        task_text=_TWO_FILE_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client_dispatching(_TWO_FILE_JUDGMENTS),
        reviewed_revision=head,
        prior=prior,
    )

    # beta was never re-examined — only alpha.py changed — so it is carried.
    beta = next(o for o in review.obligation_map if o.id == "beta")
    assert beta.carried_forward_from == base
    assert beta.coverage_status == "not_addressed"

    # And its gap is still reported, so the verdict still reflects it —
    # along with the instruction for closing it, which the agent still needs.
    assert any(f.related_obligation == "Beta behaves" for f in review.findings)

    # Both weak obligations carry a recommendation: `beta` carried forward from
    # the prior review, `alpha` derived fresh this run.
    #
    # This assertion previously read `== ["beta"]`, which encoded the defect
    # #218 removed. `alpha` is weak — it is supplied to `recommend_tests` as
    # such — and simply went without a recommendation because the stage kept
    # whatever the response returned and never reconciled it against the weak
    # set. A weak obligation with no recommendation is now an error.
    assert sorted(r.obligation_id for r in review.recommendations) == ["alpha", "beta"]
    assert review.completion is not None
    assert review.completion.verdict.value != "no_material_gaps"


def test_a_review_written_under_an_older_schema_is_skipped_not_fatal(tmp_path):
    """The store accumulates reviews across schema versions, so scanning it must
    be best-effort. A stored review this build cannot parse is one it cannot
    build on — crashing would mean any change to the review schema bricks the
    tool for every existing cache. Found by dogfooding: reviews written before
    #160 reshaped `ReviewProvenance` made `check` die on startup.
    """
    repo, first, second = _repo_with_two_commits(tmp_path)
    root = tmp_path / "reviews"
    root.mkdir()
    (root / f"{first}.json").write_text(
        f'{{"mode": "local", "reviewed_revision": "{first}",'
        ' "provenance": {"determinism_mode": "record", "model": "m",'
        ' "temperature": 0.0, "seed": null}}'
    )
    store = ReviewStore(root)

    # No prior review usable, but the run continues rather than raising.
    assert find_prior_review(store, second, repo, TASK) is None


def test_only_the_affected_obligation_is_re_derived(tmp_path):
    """Both halves of the split, at the pipeline level.

    The dogfood run reported this obligation unsupported and it was right: the
    gap-laundering test asserted the UNAFFECTED obligation was carried, but never
    that the affected one was actually re-derived. A build that carried
    everything forward would have passed it.
    """
    from acceptance.change.diff import extract_change_set
    from acceptance.pipeline import run_review
    from tests.support import client_dispatching

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "alpha.py").write_text("def alpha():\n    return 0\n")
    (repo / "beta.py").write_text("def beta():\n    return 2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "alpha.py").write_text("def alpha():\n    return 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    head = _git(repo, "rev-parse", "HEAD")

    prior = Review(
        mode="local",
        reviewed_revision=base,
        task_source=task_source_for(_TWO_FILE_TASK, "task.md"),
        obligation_map=[
            _obligation(
                "alpha",
                description="Alpha behaves",
                coverage_refs=["alpha.py#@@ -1 +1 @@"],
                coverage_status="not_addressed",  # the stale judgment
                evidence_class="unsupported",
            ),
            _obligation(
                "beta",
                description="Beta behaves",
                coverage_refs=["beta.py#@@ -1 +1 @@"],
            ),
        ],
    )

    review = run_review(
        task_text=_TWO_FILE_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client_dispatching(_TWO_FILE_JUDGMENTS),
        reviewed_revision=head,
        prior=prior,
    )

    by_id = {o.id: o for o in review.obligation_map}
    # alpha.py changed, so alpha was judged again — and the fresh judgment
    # replaced the stale one rather than the prior verdict surviving.
    assert by_id["alpha"].carried_forward_from is None
    assert by_id["alpha"].coverage_status == "addressed"
    # beta.py did not, so beta was not re-judged.
    assert by_id["beta"].carried_forward_from == base


def test_exactly_one_prior_review_is_used_even_when_several_are_candidates(tmp_path):
    """One prior review and one new head — the task's stated boundary.

    Two ancestors both have stored reviews. The nearest is used *whole*: the
    further one contributes nothing, rather than the two being merged into a
    combined history no reviewer ever produced.
    """
    repo, first, second = _repo_with_two_commits(tmp_path)
    (repo / "rounding.py").write_text("def f():\n    return 3\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "third")
    third = _git(repo, "rev-parse", "HEAD")

    store = ReviewStore(tmp_path / "reviews")
    store.write(_review(first, [_obligation("only-in-the-older-review")]))
    store.write(_review(second, [_obligation("only-in-the-nearer-review")]))

    prior = find_prior_review(store, third, repo, TASK)

    assert prior is not None
    assert prior.reviewed_revision == second
    assert [o.id for o in prior.obligation_map] == ["only-in-the-nearer-review"]


def test_nothing_from_a_non_selected_ancestor_review_reaches_the_rerun(tmp_path):
    """ "One prior review" at the pipeline level, not just at the selector.

    The dogfood run asked for this twice. Its literal phrasing — that the input
    model take a single review rather than a list — is a type signature, which
    pytest cannot fail on. The meaningful runtime version is this: with two
    ancestor reviews stored, nothing from the one NOT selected may appear in the
    result. A build that merged both would produce a review whose history no
    single run ever established.
    """
    from acceptance.cli import run_check
    from acceptance.config import RunConfig
    from tests.support import client_dispatching

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "alpha.py").write_text("def alpha():\n    return 1\n")
    (repo / "beta.py").write_text("def beta():\n    return 2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "first")
    first = _git(repo, "rev-parse", "HEAD")
    (repo / "beta.py").write_text("def beta():\n    return 2  # touched\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "second")
    second = _git(repo, "rev-parse", "HEAD")
    (repo / "beta.py").write_text("def beta():\n    return 2  # touched again\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "third")
    third = _git(repo, "rev-parse", "HEAD")

    store = ReviewStore(tmp_path / "reviews")
    stale_finding = Finding(
        type="coverage_gap",
        severity="high",
        description="a gap only the FURTHER review ever recorded",
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="requirement", ref="task.md:1")],
        related_obligation="Alpha behaves",
    )
    for revision, findings in ((first, [stale_finding]), (second, [])):
        store.write(
            Review(
                mode="local",
                reviewed_revision=revision,
                task_source=task_source_for(_TWO_FILE_TASK, "task.md"),
                obligation_map=[
                    _obligation(
                        "alpha",
                        description="Alpha behaves",
                        coverage_refs=["alpha.py#@@ -1 +1 @@"],
                    ),
                    _obligation(
                        "beta",
                        description="Beta behaves",
                        coverage_refs=["beta.py#@@ -1 +1 @@"],
                    ),
                ],
                findings=findings,
            )
        )

    task_file = tmp_path / "task.md"
    task_file.write_text(_TWO_FILE_TASK)
    review = run_check(
        task=str(task_file),
        base=second,
        head=third,
        config=RunConfig(),
        store=store,
        repo=repo,
        client=client_dispatching(_TWO_FILE_JUDGMENTS),
    )

    assert review.delta is not None
    assert review.delta.prior_reviewed_revision == second
    # alpha is carried — but from the SELECTED review, not the further one...
    alpha = next(o for o in review.obligation_map if o.id == "alpha")
    assert alpha.carried_forward_from == second
    # ...and the finding only the further review held never appears.
    assert all("only the FURTHER review" not in finding.description for finding in review.findings)


def test_a_working_tree_review_builds_on_the_review_of_head(tmp_path):
    """§5.1's path: a check runs before a commit exists.

    Its `reviewed_revision` is `<working-tree>`, which git cannot resolve, so
    without an explicit anchor no prior review is ever found and the whole
    incremental feature is unreachable from the primary local path. Found by
    dogfooding: this project's own runs silently never used it.
    """
    repo, _first, second = _repo_with_two_commits(tmp_path)
    store = ReviewStore(tmp_path / "reviews")
    store.write(_review(second, [_obligation("a")]))

    prior = find_prior_review(store, "<working-tree>", repo, TASK, ancestry_ref=second)

    # The review OF head is a legitimate predecessor of the working tree.
    assert prior is not None and prior.reviewed_revision == second
