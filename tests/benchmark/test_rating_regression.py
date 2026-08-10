"""#190: the rating-stability corpus as an executable regression suite.

DR-180's load-bearing criterion — `strongly supported` is not issued on evidence
that does not earn it — had no scoreboard. Every candidate fix to the
evidence-judgement stage was accepted or rejected by eyeball. These are the
assertions that replace the eyeball.

The suite must fail in both directions. A judge that rates everything strongly
supported must fail it, and so must a judge that rates nothing strongly
supported, because "stop moving" is a fix that passes a one-directional suite
while losing all seven real gaps the corpus records.
"""

import json
from pathlib import Path

import pytest

from acceptance.benchmark.corpus import (
    build_corpus_case,
    load_labels,
    remove_corpus_worktree,
)
from acceptance.benchmark.coverage import classify_case
from acceptance.benchmark.scoring import score_case_set
from tests.benchmark.degenerate_judges import degenerate_client

REPO = Path(__file__).resolve().parents[2]
CASES_DIR = REPO / "tests" / "fixtures" / "rating-regression"
CORPUS_DIR = REPO / "tests" / "fixtures" / "rating-stability"
CASE_DIRS = sorted(p for p in CASES_DIR.iterdir() if p.is_dir())

# The corpus's own ground-truth tables, restated as (run, obligation) pairs so a
# label silently dropped from a fixture fails here rather than shrinking the
# suite. Transcribed from the tables in #190 and `current-task.md`.
UNEARNED_STRONG = {
    ("167-gate2-run1", "default-to-most-recent-review"),
    ("167-gate2-run1", "no-speculative-writing"),
    ("167-gate2-run1", "remove-stale-next-instruction-file"),
    ("167-gate2-run1", "spec-no-longer-describes-written-file"),
    ("167-gate2-run1", "retrieve-from-stored-review-state"),
    ("167-gate2-run2", "no-speculative-writing"),
    ("167-gate2-run2", "remove-stale-next-instruction-file"),
}

REAL_GAPS = {
    ("167-gate2-run1", "fixed-command-surface"),
    ("167-gate2-run1", "replace-written-file-with-command"),  # partly real
    ("167-gate2-run2", "default-to-most-recent-review"),
    ("167-gate2-run2", "retrieve-from-stored-review-state"),
    ("167-gate2-run3", "remove-stale-next-instruction-file"),  # the silent --json deletion
    ("167-gate2-run3", "no-speculative-writing"),
    ("167-gate2-run3", "spec-no-longer-describes-written-file"),
    ("167-gate2-run4", "preserve-prose-structured-fields"),
}


@pytest.fixture
def corpus_worktrees(tmp_path):
    """A root for materialized worktrees, deregistered from the main repo after.

    Worktree registration lives in this repository's `.git`, so deleting
    tmp_path alone would leave stale entries accumulating across runs.
    """
    yield tmp_path
    for path in sorted(tmp_path.rglob("wt*")):
        if path.is_dir():
            remove_corpus_worktree(REPO, path)


def _labels(case_dir: Path) -> dict:
    return json.loads((case_dir / "labels.json").read_text())


def _classes(case_dir: Path) -> dict[str, str]:
    return {o["id"]: o["evidence_class"] for o in _labels(case_dir)["obligations"]}


# --------------------------------------------------------------------------
# The ground truth is encoded at all
# --------------------------------------------------------------------------


def test_every_unearned_rating_is_required_to_no_longer_be_issued():
    """Each rating the corpus records as unearned is labelled as something
    other than `strongly supported`, so a judge that reissues it disagrees."""
    for run, obligation in sorted(UNEARNED_STRONG):
        klass = _classes(CASES_DIR / run)[obligation]
        assert klass != "strongly_supported", f"{run}/{obligation} is labelled {klass}"


def test_every_real_gap_is_required_to_still_be_reported():
    """Each gap the corpus confirms was real is a ground-truth gap, so a fix
    that blunts it away loses gap recall rather than passing quietly."""
    for run, obligation in sorted(REAL_GAPS):
        gaps = {g["obligation_id"] for g in _labels(CASES_DIR / run)["gaps"]}
        assert obligation in gaps, f"{run} has no ground-truth gap for {obligation}"


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=lambda p: p.name)
def test_labels_load_against_the_shared_ground_truth_schema(case_dir):
    """Cases use `GroundTruthLabels`, not a shape invented for this task — so
    its validators (unique ids, resolvable gap links, no unexplained result)
    apply here too."""
    labels = load_labels(case_dir)
    assert labels.obligations
    assert all(o.evidence_rationale.strip() for o in labels.obligations)


# --------------------------------------------------------------------------
# Both directions
# --------------------------------------------------------------------------


def test_the_case_set_can_catch_a_judge_erring_either_way():
    """Both-directions is a property of the case MIX, not of new scoring code.

    `evidence_agreement` is recall over (description, evidence_class) pairs, so a
    judge that always says `strongly_supported` can only match obligations whose
    ground truth is that, and one that never says it can only match the rest. A
    set holding just one kind would let one degenerate judge through.
    """
    everything = [klass for d in CASE_DIRS for klass in _classes(d).values()]
    assert "strongly_supported" in everything
    assert [k for k in everything if k != "strongly_supported"]


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=lambda p: p.name)
def test_no_case_passes_trivially(case_dir):
    """Every case has to be able to fail something.

    `163-gate2-run1` is the one this exists for. It is a clean run kept as a
    control, so it has no gaps and no sub-strong ratings — and the issue warns
    against letting it become the case that passes trivially. Its bite is the
    other direction: with zero ground-truth gaps, a judge that flags anything
    here loses gap *precision*.
    """
    labels = _labels(case_dir)
    classes = set(_classes(case_dir).values())
    catches_permissive = bool(classes - {"strongly_supported"}) or bool(labels["gaps"])
    catches_pessimistic = "strongly_supported" in classes or not labels["gaps"]
    assert catches_permissive or catches_pessimistic


def _score_with(always_strong: bool, tmp_path):
    cases = []
    for index, case_dir in enumerate(CASE_DIRS):
        case = build_corpus_case(case_dir, REPO, CORPUS_DIR, tmp_path / f"wt{index}")
        obligations = [
            {"id": o["id"], "description": o["description"]}
            for o in _labels(case_dir)["obligations"]
        ]
        client = degenerate_client(obligations, always_strong=always_strong)
        cases.append(classify_case(case, client))
    return score_case_set(cases)


def test_a_judge_that_always_issues_strongly_supported_fails_the_suite(corpus_worktrees):
    report = _score_with(always_strong=True, tmp_path=corpus_worktrees)
    # It agrees on the genuinely-strong obligations and on nothing else, so it
    # cannot reach full agreement...
    assert report.evidence_agreement < 1.0
    # ...and having found nothing wrong, it reports none of the real gaps.
    assert report.gap_recall < 1.0


def test_a_judge_that_never_issues_strongly_supported_fails_the_suite(corpus_worktrees):
    report = _score_with(always_strong=False, tmp_path=corpus_worktrees)
    assert report.evidence_agreement < 1.0
    # Absence of false STRONGs is explicitly not sufficient on its own (#190):
    # flagging everything costs precision even where recall looks healthy.
    assert report.gap_precision < 1.0


def test_the_two_degenerate_judges_disagree_about_the_ratings(corpus_worktrees):
    """Guards the harness rather than the judge.

    If the stub's verdict never reached `strength.py`, both judges would score
    identically and the two tests above would pass for the wrong reason — the
    'helper the pipeline never actually calls' hole that defect injection keeps
    finding here.
    """
    permissive = _score_with(always_strong=True, tmp_path=corpus_worktrees / "a")
    pessimistic = _score_with(always_strong=False, tmp_path=corpus_worktrees / "b")
    assert permissive.evidence_agreement != pessimistic.evidence_agreement


# --------------------------------------------------------------------------
# The task's own requirements
#
# Gate 2 rated all of the following `unsupported` — no mapped test at all — and
# the mapping audit for that run came back 100% populated with zero foreign
# ids, so the finding was the review being right rather than half-blind. These
# are the assertions that were missing.
# --------------------------------------------------------------------------

CORPUS_RUN_FILES = {"current-task.md", "check-output.log", "judgement.md"}


def test_scoring_goes_through_the_shared_benchmark_path(monkeypatch, corpus_worktrees):
    """The suite must score through `benchmark/scoring.py`, not a private copy.

    A second scoring implementation would drift from the canonical one exactly
    the way the CLI and benchmark pipelines drifted before M7.4 — and the
    divergence would be invisible, because both would keep returning numbers.
    """
    import acceptance.benchmark.scoring as scoring

    calls = []
    real = scoring.score_case_set

    def tracking(cases, client=None):
        calls.append(len(cases))
        return real(cases, client)

    monkeypatch.setattr(scoring, "score_case_set", tracking)
    # Patch THIS module's global, via globals() rather than by importing the
    # module by name: pytest may import it under a different name, in which
    # case `import tests.benchmark.test_rating_regression` yields a second
    # module object and patching it leaves the name `_score_with` resolves
    # untouched — the test then passes an empty call list forever.
    monkeypatch.setitem(globals(), "score_case_set", tracking)

    report = _score_with(always_strong=True, tmp_path=corpus_worktrees)

    assert calls == [len(CASE_DIRS)]
    assert report.evidence_agreement is not None


def test_no_case_issues_a_live_model_call(corpus_worktrees, monkeypatch):
    """Every model call is served by the injected stub, so the suite cannot
    reach a provider. Asserted by counting: a call that bypassed the stub would
    leave the count below the number of pipeline stages."""
    seen: list[str] = []
    case = build_corpus_case(CASE_DIRS[0], REPO, CORPUS_DIR, corpus_worktrees / "wt0")
    obligations = [
        {"id": o["id"], "description": o["description"]}
        for o in _labels(CASE_DIRS[0])["obligations"]
    ]
    client = degenerate_client(obligations, always_strong=True)
    inner = client._completion_fn

    def counting(**kwargs):
        seen.append(kwargs["response_format"]["json_schema"]["name"])
        return inner(**kwargs)

    # The injected stub is the only thing standing between the pipeline and a
    # provider, so wrapping it is how "no live call" becomes observable.
    monkeypatch.setattr(client, "_completion_fn", counting)
    classify_case(case, client)

    assert "_Decomposition" in seen and "_Mappings" in seen
    assert "_Discrimination" in seen or "_Coverage" in seen


def test_no_model_transcript_is_committed_into_the_fixtures():
    """A transcript embeds the full request, so committing one here would put
    this repository's own diffs and task text into `tests/fixtures/` — the thing
    the corpus avoided by storing rendered reports."""
    for case_dir in CASE_DIRS:
        assert {p.name for p in case_dir.iterdir()} == {"case.json", "labels.json"}
    for run in CORPUS_DIR.iterdir():
        if run.is_dir():
            assert {p.name for p in run.iterdir()} <= CORPUS_RUN_FILES


def test_the_corpus_itself_is_untouched_apart_from_its_readme():
    """The corpus is the evidence record these assertions derive from. Editing
    it to suit a test would destroy the thing being tested against."""
    assert (CORPUS_DIR / "README.md").is_file()
    assert (CORPUS_DIR / "revisions.txt").is_file()
    for run in sorted(p for p in CORPUS_DIR.iterdir() if p.is_dir()):
        assert {p.name for p in run.iterdir()} == CORPUS_RUN_FILES, run.name


def test_the_scoreboard_is_committed_as_fixtures_for_every_run():
    """All six runs, committed — not generated at test time, where a case could
    quietly stop existing."""
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "tests/fixtures/rating-regression"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    runs = {Path(p).parent.name for p in tracked}
    assert runs == {p.name for p in CASE_DIRS}
    assert len(runs) == 6
    for case_dir in CASE_DIRS:
        for name in ("case.json", "labels.json"):
            assert f"tests/fixtures/rating-regression/{case_dir.name}/{name}" in tracked


def _tree_digest(root: Path) -> dict[str, str]:
    import hashlib

    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def test_running_the_suite_does_not_alter_the_judgement_stage(corpus_worktrees):
    """This task builds the scoreboard; the judgement stage is untouched.

    Asserted by running a case and digesting the stage's source either side,
    rather than by grepping this file for import names — a source grep matches
    the very string the assertion is written with, so it can only ever be
    self-referential.
    """
    stage = REPO / "src" / "acceptance" / "evidence"
    coverage_stage = REPO / "src" / "acceptance" / "coverage"
    before = (_tree_digest(stage), _tree_digest(coverage_stage))

    case = build_corpus_case(CASE_DIRS[0], REPO, CORPUS_DIR, corpus_worktrees / "wt0")
    obligations = [
        {"id": o["id"], "description": o["description"]}
        for o in _labels(CASE_DIRS[0])["obligations"]
    ]
    classify_case(case, degenerate_client(obligations, always_strong=True))

    assert (_tree_digest(stage), _tree_digest(coverage_stage)) == before


def test_the_decompose_stability_corpus_gains_no_regression_artifacts():
    """A separate task (#195). This one must not seed cases there — the give-away
    would be `case.json`/`labels.json` appearing in a corpus that holds only
    dogfood-run prose."""
    other = REPO / "tests" / "fixtures" / "decompose-stability"
    if not other.exists():
        pytest.skip("decompose-stability corpus not present")
    names = {p.name for p in other.rglob("*") if p.is_file()}
    assert not names & {"case.json", "labels.json"}
    # And this suite reads only from its own corpus.
    assert CORPUS_DIR.name == "rating-stability"
    assert other not in CORPUS_DIR.parents and other != CORPUS_DIR


def test_cases_carry_only_their_run_input_not_resumed_state(corpus_worktrees):
    """Runs 2 and 3 were incremental re-runs (M7.5) resuming stored review
    state. A case supplies the run's *input*; restoring what it resumed from is
    out of scope, so nothing here may carry it in."""
    case = build_corpus_case(
        CASES_DIR / "167-gate2-run2", REPO, CORPUS_DIR, corpus_worktrees / "wt0"
    )
    assert case.inputs.declaration_text is None
    assert case.reviewer_output is None
    assert case.score is None
    # The worktree is a checkout of the revision alone — no carried-over review.
    assert not (Path(case.inputs.repo) / ".acceptance").exists()


def test_the_readme_states_what_is_and_is_not_read():
    readme = (CORPUS_DIR / "README.md").read_text()
    assert "Not currently read by any test" not in readme
    assert "test_rating_regression.py" in readme
    # The honest half: the judgements are transcribed by hand, not parsed.
    assert "judgement.md" in readme


# --- The two rewritten judgements ------------------------------------------
#
# Runs 3 and 5 preserve both the original and the corrected reading. The
# corrected one is ground truth in each, and getting this backwards is the
# specific failure the corpus exists to prevent: run 3's original reading
# called all three findings tool defects and would have shipped the silent
# `--json` deletion.


def test_run3_encodes_the_corrected_reading_that_all_three_findings_were_real():
    meta = json.loads((CASES_DIR / "167-gate2-run3" / "case.json").read_text())
    assert "REWRITTEN" in meta["judgement"]
    assert "corrected reading is ground truth" in meta["judgement"]

    classes = _classes(CASES_DIR / "167-gate2-run3")
    gaps = {g["obligation_id"] for g in _labels(CASES_DIR / "167-gate2-run3")["gaps"]}
    for obligation in (
        "remove-stale-next-instruction-file",
        "no-speculative-writing",
        "spec-no-longer-describes-written-file",
    ):
        assert classes[obligation] != "strongly_supported"
        assert obligation in gaps, f"{obligation} must be a real gap, not a tool defect"


def test_run5_encodes_the_corrected_reading_that_run4s_strong_was_right():
    meta = json.loads((CASES_DIR / "167-gate2-run5" / "case.json").read_text())
    assert "REWRITTEN" in meta["judgement"]

    # Run 5's own output said `partially supported`; the rewritten judgement
    # calls that a wrong M5.2 verdict and run 4's `strongly supported` correct.
    assert _classes(CASES_DIR / "167-gate2-run5")["replace-written-file-with-command"] == (
        "strongly_supported"
    )
    assert _classes(CASES_DIR / "167-gate2-run4")["replace-written-file-with-command"] == (
        "strongly_supported"
    )
    assert not _labels(CASES_DIR / "167-gate2-run5")["gaps"]


def test_the_labels_still_show_the_instability_rather_than_smoothing_it():
    """This task measures the instability; it does not reduce it. If every run
    carried the same class for the same obligation, the corpus's central
    finding would have been normalised away by the act of encoding it."""
    by_obligation: dict[str, set[str]] = {}
    for case_dir in CASE_DIRS:
        for oid, klass in _classes(case_dir).items():
            by_obligation.setdefault(oid, set()).add(klass)

    moved = {o: c for o, c in by_obligation.items() if len(c) > 1}
    assert len(moved) >= 5, f"only {len(moved)} obligations disagree across runs"
    assert "remove-stale-next-instruction-file" in moved


def test_each_case_is_scored_through_score_case_itself(corpus_worktrees):
    """`score_case_set` aggregates via `_all_counts` and never calls
    `score_case`, so asserting the set-level entrypoint alone left the stated
    constraint — cases are scored through `score_case` — satisfied only in
    spirit. This scores every case through `score_case` directly and requires
    the two paths to agree, so a private scorer cannot diverge unnoticed.
    """
    import acceptance.benchmark.scoring as scoring

    scored, seen = [], []
    real = scoring.score_case

    def spy(case, client=None):
        seen.append(case.case_id)
        return real(case, client)

    for index, case_dir in enumerate(CASE_DIRS):
        case = build_corpus_case(case_dir, REPO, CORPUS_DIR, corpus_worktrees / f"wt{index}")
        obligations = [
            {"id": o["id"], "description": o["description"]}
            for o in _labels(case_dir)["obligations"]
        ]
        scored.append(classify_case(case, degenerate_client(obligations, always_strong=True)))

    per_case = [spy(case) for case in scored]
    assert seen == [c.case_id for c in scored]
    assert per_case == score_case_set(scored).per_case


def test_no_provider_is_ever_contacted(corpus_worktrees, monkeypatch):
    """The stronger form of "no live call": make the provider entrypoint itself
    fail. `llm._default_completion_fn` calls `litellm.completion`, so a stage
    that slipped past the injected stub would raise here instead of quietly
    reaching the network."""
    import litellm

    def explode(*args, **kwargs):
        raise AssertionError("a live provider call was attempted")

    monkeypatch.setattr(litellm, "completion", explode)

    case = build_corpus_case(CASE_DIRS[0], REPO, CORPUS_DIR, corpus_worktrees / "wt0")
    obligations = [
        {"id": o["id"], "description": o["description"]}
        for o in _labels(CASE_DIRS[0])["obligations"]
    ]
    scored = classify_case(case, degenerate_client(obligations, always_strong=True))
    assert scored.reviewer_output is not None


# The one sanctioned transcript corpus: #146's recorded prompt-quality fixtures.
# It predates this task and is deliberately committed; everything else under
# tests/fixtures/ must stay transcript-free.
SANCTIONED_TRANSCRIPTS = REPO / "tests" / "fixtures" / "transcripts"


def test_no_transcript_lives_anywhere_under_the_fixture_tree():
    """Wider than the two case directories, because the stated defect is a
    transcript stored *elsewhere* in the repository. A transcript embeds the
    full request, so one committed here would leak this repo's own diffs and
    task text into versioned test data."""
    fixtures = REPO / "tests" / "fixtures"
    suspects = []
    for path in fixtures.rglob("*"):
        if not path.is_file() or SANCTIONED_TRANSCRIPTS in path.parents:
            continue
        if path.suffix not in {".json", ".jsonl", ".txt", ".md", ".log"}:
            continue
        head = path.read_text(errors="ignore")[:4000]
        if '"response"' in head and '"messages"' in head:
            suspects.append(str(path.relative_to(REPO)))
    assert not suspects, f"transcript-like files outside the sanctioned corpus: {suspects}"


def test_the_sanctioned_corpus_grows_only_by_explicit_approval():
    """#146's corpus is for prompt-quality tests recorded against fixtures,
    never against this repository's own dogfood runs.

    This was a literal count, which said "this task added nothing" and expired
    the moment another task legitimately recorded one (#144 added two, against a
    synthetic invoice-export task). A number in a second file is a proxy for the
    real rule and re-arms the same failure on every sanctioned recording, so it
    delegates to the manifest instead: a new transcript still cannot appear
    without an explicit entry there, and `test_corpus_mechanism.py` proves each
    entry carries the markers of the fixture it claims to come from.
    """
    from tests.prompts.test_corpus_mechanism import _APPROVED_TRANSCRIPTS

    present = {path.name for path in SANCTIONED_TRANSCRIPTS.glob("*.json")}

    assert present == set(_APPROVED_TRANSCRIPTS)
