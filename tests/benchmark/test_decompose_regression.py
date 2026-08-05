"""#195: the decompose-stability corpus as an executable regression suite.

#193 had no scoreboard. Its counterpart #191 has one — #190 built it for the
evidence-judgement stage — and the same reasoning applies here: until the corpus
findings are assertions, any decompose fix is judged by eyeball, and this is the
corpus where eyeballing already failed twice, in writing.

Seven cases come from `tests/fixtures/decompose-stability/`. The eighth comes
from `dogfood-logs/195-gate1-run1/`, this task's own Gate 1 run, which did not
pass: nine requirements produced no obligation and three open questions were
raised that the task file answers. It is the strongest case here, because its
input was authored knowing what the decomposition should contain, so its losses
are enumerated rather than reconstructed.

## What the ground truth is, and what it is not

Ground truth per case is **the obligations and questions the corpus judged**, not
a complete expected decomposition. Transcribing each run's full output as ground
truth would assert that what the run produced is correct — which for these runs
is the thing in dispute. Run 6's judgement says in terms that its breakdown was
not accurate. So `decomposition_accuracy` here is recall over the judged subset,
and that is the honest reading of it.

## Content and shape are different findings

The corpus README's governing distinction, and the reason this file separates
them. A **content** difference is something present in one run and absent in
another — something was lost, and a determinism layer that pinned the output
would freeze the loss in place. A **shape** difference is the same content
partitioned differently, which is what a determinism layer is for and must never
be counted against decomposition quality.

The distinction has a sharp consequence for precision. `align_obligations` is
bijective, so a run that splits one ground-truth obligation into three leaves two
reviewer obligations unmatched — **indistinguishable from two inventions**.
Precision therefore cannot be asserted on a case whose ground truth records a
legitimate re-split, and `SHAPE_DIFFERENCE_RUNS` names those cases so the
exclusion is explicit rather than an accident of which assertions were written.
"""

import json
from pathlib import Path

import pytest

from acceptance.benchmark.corpus import (
    MissingRunInputError,
    build_decompose_case,
    load_decompose_meta,
)
from acceptance.benchmark.decomposition import decompose_case
from acceptance.benchmark.scoring import score_case, score_case_set
from tests.benchmark.degenerate_decomposers import decomposer

REPO = Path(__file__).resolve().parents[2]
CASES_DIR = REPO / "tests" / "fixtures" / "decompose-regression"
CORPUS_DIR = REPO / "tests" / "fixtures" / "decompose-stability"
CASE_DIRS = sorted(p for p in CASES_DIR.iterdir() if p.is_dir())

# The corpus's own findings, restated as (run, obligation) pairs so a label
# silently dropped from a fixture fails here rather than shrinking the suite.
# Transcribed from the tables in #195 and the run judgements they cite.

# Content present in the task file and absent from the decomposition over it.
CONTENT_LOSSES = {
    ("189-gate1-run4", "report-open-questions-present-in-some-runs-only"),
    ("189-gate1-run6", "report-only-no-acceptance-decision"),
    ("195-gate1-run1", "lossy-decomposer-fails"),
    ("195-gate1-run1", "question-raising-decomposer-fails"),
    ("195-gate1-run1", "sentence-splitting-decomposer-fails"),
    ("195-gate1-run1", "no-case-passes-trivially"),
    ("195-gate1-run1", "no-deciding-provenance-type"),
    ("195-gate1-run1", "no-resample-variance-measurement"),
    ("195-gate1-run1", "no-new-corpus-runs"),
    ("195-gate1-run1", "no-rating-stability-work"),
    ("195-gate1-run1", "no-corpus-modification"),
}

# Statically-checkable prohibitions the corpus records typed `human_review`,
# which is a mandatory Gate 2 pause under CLAUDE.md — as typed they block a
# clean gate by construction, forever, whatever code is written.
MISTYPED_HUMAN_REVIEW = {
    ("189-gate1-run7", "no-acceptability-threshold"),
    ("189-gate1-run7", "no-threshold-or-rating"),
    ("189-gate1-run7", "no-variance-reduction"),
    ("195-gate1-run1", "preserve-no-thresholding"),
    ("195-gate1-run1", "preserve-no-variance-reduction"),
}

# Every run whose task file names a symbol in an obligation's source.
SYMBOL_RUNS = {
    "189-gate1-run2",
    "189-gate1-run3",
    "189-gate1-run4",
    "189-gate1-run5",
    "189-gate1-run6",
    "189-gate1-run7",
}

# Cases whose ground truth records a legitimate re-split or re-bundle, where
# precision is not a quality signal. Run 3->4 turned one unchanged sentence into
# three obligations; run 5->6 bundled two pairs into one each. Both directions
# occur, so a metric that only notices splits misses half of it.
SHAPE_DIFFERENCE_RUNS = {"189-gate1-run4", "189-gate1-run6"}

# The two runs whose judgements were made wrong and corrected in place, with
# both readings preserved. The corrected reading is ground truth, and each case
# has to say so rather than leaving a reader to infer it.
CONTESTED_READING_RUNS = {"189-gate1-run4", "189-gate1-run6"}


def _labels(case_dir: Path) -> dict:
    return json.loads((case_dir / "labels.json").read_text())


def _obligations(case_dir: Path) -> dict[str, dict]:
    return {o["id"]: o for o in _labels(case_dir)["obligations"]}


def _questions(case_dir: Path) -> dict[str, dict]:
    return {q["id"]: q for q in _labels(case_dir)["open_questions"]}


def _case(case_dir: Path):
    return build_decompose_case(case_dir, REPO)


def _scored(case_dir: Path, behaviour: str):
    case = _case(case_dir)
    return decompose_case(case, decomposer(case.ground_truth, behaviour=behaviour))


# --------------------------------------------------------------------------
# The ground truth is encoded at all
# --------------------------------------------------------------------------


def test_every_content_loss_is_required_to_be_reported():
    """Each requirement the corpus records as producing no obligation is a
    ground-truth obligation, so a decomposer that drops it loses recall rather
    than passing quietly."""
    for run, obligation in sorted(CONTENT_LOSSES):
        assert obligation in _obligations(CASES_DIR / run), (
            f"{run} has no ground-truth obligation for {obligation}"
        )


def test_every_mistyped_prohibition_is_required_to_carry_another_type():
    """Each prohibition the corpus records typed `human_review` carries an
    expected type that is not `human_review`, so reissuing it disagrees."""
    for run, obligation in sorted(MISTYPED_HUMAN_REVIEW):
        expected = _obligations(CASES_DIR / run)[obligation].get("expected_type")
        assert expected is not None, f"{run}/{obligation} has no expected_type"
        assert expected != "human_review", f"{run}/{obligation} expects {expected}"


def test_the_output_format_question_is_required_on_every_corpus_case():
    """The task file never answers it in any of the seven versions, so its
    *dropping* is the defect and not its presence."""
    for case_dir in CASE_DIRS:
        if not case_dir.name.startswith("189-"):
            continue
        question = _questions(case_dir).get("report-format")
        assert question is not None, f"{case_dir.name} does not label it"
        assert question["should_be_raised"] is True


def test_questions_the_task_file_answers_are_required_not_to_be_raised():
    """#178's direction. Encoded as ground truth rather than left implicit, so a
    decomposer cannot be rewarded for raising everything."""
    questions = _questions(CASES_DIR / "195-gate1-run1")
    forbidden = {qid for qid, q in questions.items() if not q["should_be_raised"]}
    assert forbidden == {
        "clarify-record-run-provenance-type",
        "clarify-run-4-reading",
        "clarify-run-6-reading",
    }


def test_symbols_named_in_the_task_file_are_required_of_the_obligation():
    """A symbol requirement rides on its own field, because it cannot ride on
    description matching — the aligner correctly matches an obligation that
    dropped the symbol to one that kept it."""
    for case_dir in CASE_DIRS:
        if case_dir.name not in SYMBOL_RUNS:
            continue
        required = {
            symbol
            for o in _labels(case_dir)["obligations"]
            for symbol in o.get("required_symbols", [])
        }
        assert required, f"{case_dir.name} requires no symbol"
        task_text = _case(case_dir).inputs.task_text
        for symbol in required:
            assert symbol in task_text, (
                f"{case_dir.name} requires {symbol!r}, which its task file does "
                f"not name — a requirement with no source"
            )


@pytest.mark.parametrize(
    "case_dir", [CASES_DIR / r for r in sorted(CONTESTED_READING_RUNS)], ids=sorted(CONTESTED_READING_RUNS)
)
def test_a_contested_case_records_which_reading_is_ground_truth(case_dir):
    """Runs 4 and 6 preserve both a wrong judgement and its correction. Which
    one governs is a human decision and has to be written down, not inferred at
    test-writing time."""
    meta = load_decompose_meta(case_dir)
    assert "judgement.md" in meta.judgement
    lowered = meta.judgement.lower()
    assert "ground truth is" in lowered
    assert "not ground truth" in lowered or "preserved" in lowered


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=lambda p: p.name)
def test_labels_load_against_the_shared_ground_truth_schema(case_dir):
    """Cases use `GroundTruthLabels`, not a shape invented for this task — so
    its validators (unique ids, no unexplained result) apply here too."""
    labels = build_decompose_case(case_dir, REPO).ground_truth
    assert labels.obligations
    assert all(o.evidence_rationale.strip() for o in labels.obligations)
    assert all(q.rationale.strip() for q in labels.open_questions)


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=lambda p: p.name)
def test_no_case_passes_trivially(case_dir):
    """Every case has to be able to fail something.

    Runs 3 and 4 are the ones this exists for. They are the corpus's clean
    sheets — 20 obligations, zero open questions — and the issue warns they are
    the trap the corpus records rather than the control: a clean run reached
    because questions vanished is not one reached because they were answered.

    Asserted by scoring rather than by inspecting the fixture's shape: "this
    case has some labels" is a restatement of the file, while "a degenerate
    decomposer scores below 1.0 on this case" is the property actually wanted.
    Each case must fail at least one direction; that the *set* covers both is a
    separate test, because no single case is required to catch everything.
    """
    lossy = score_case(_scored(case_dir, "lossy"))
    permissive = score_case(_scored(case_dir, "permissive"))

    def imperfect(value: float | None) -> bool:
        # None means the ground truth takes no position on that metric here,
        # which is not a failure the case can claim credit for.
        return value is not None and value < 1.0

    assert (
        imperfect(lossy.decomposition_accuracy)
        or imperfect(lossy.open_question_recall)
        or imperfect(permissive.decomposition_precision)
        or imperfect(permissive.open_question_precision)
    ), f"{case_dir.name} is passed by both degenerate decomposers"


# --------------------------------------------------------------------------
# Both directions, through the shared scoring path
# --------------------------------------------------------------------------


def _report(behaviour: str):
    return score_case_set([_scored(d, behaviour) for d in CASE_DIRS])


def test_a_faithful_decomposer_scores_perfectly():
    """The guard that makes the two failure tests mean anything.

    Without it, a metric wired to return 0.0 for everyone would satisfy every
    `< 1.0` assertion below and the suite would pass while measuring nothing.
    """
    report = _report("faithful")
    assert report.decomposition_accuracy == 1.0
    assert report.decomposition_precision == 1.0
    assert report.open_question_recall == 1.0
    assert report.open_question_precision == 1.0
    assert report.obligation_type_accuracy == 1.0


def test_a_decomposer_that_drops_content_fails_the_suite():
    report = _report("lossy")
    # Content it never extracted...
    assert report.decomposition_accuracy < 1.0
    # ...and the questions it stopped raising. Silence is the cheapest way to
    # look stable, so it has to cost something.
    assert report.open_question_recall < 1.0


def test_a_decomposer_that_raises_everything_and_splits_everything_fails_the_suite():
    report = _report("permissive")
    # It loses nothing, so recall cannot see it — which is the whole point.
    assert report.decomposition_accuracy == 1.0
    # Raising every question, including the ones the task file answers (#178).
    assert report.open_question_precision < 1.0
    # And inventing obligations, which only precision charges for.
    assert report.decomposition_precision < 1.0


def test_the_two_degenerate_decomposers_fail_on_different_metrics():
    """Guards the suite rather than the decomposer.

    If both failures showed up on the same number, one of the two directions
    would be unmeasured and the suite would be one-directional while looking
    like it was not.
    """
    lossy = _report("lossy")
    permissive = _report("permissive")
    assert lossy.decomposition_accuracy < permissive.decomposition_accuracy
    assert permissive.decomposition_precision < lossy.decomposition_precision
    assert permissive.open_question_recall > lossy.open_question_recall


def test_content_loss_and_shape_difference_are_scored_separately():
    """The corpus README's governing distinction, asserted rather than assumed.

    A re-split loses precision without losing content; a content loss loses
    recall. If one metric moved for both, the fix driven by it would be the
    wrong fix — a determinism layer pinning a loss in place.
    """
    lossy = _report("lossy")
    permissive = _report("permissive")
    assert lossy.decomposition_precision == 1.0, "a loss must not read as over-decomposition"
    assert permissive.decomposition_accuracy == 1.0, "a re-shape must not read as a loss"


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=lambda p: p.name)
def test_precision_is_not_asserted_where_a_re_split_is_ground_truth(case_dir):
    """`align_obligations` is bijective, so a 1->3 re-split leaves two reviewer
    obligations unmatched and is indistinguishable from two inventions. On the
    cases whose ground truth records a legitimate re-split, precision is not a
    quality signal and this suite must not read it as one."""
    if case_dir.name not in SHAPE_DIFFERENCE_RUNS:
        return
    score = score_case(_scored(case_dir, "faithful"))
    # The faithful decomposer matches the recorded shape exactly, so precision
    # is 1.0 here — and the point is that a DIFFERENT shape carrying the same
    # content would score lower without anything having been lost.
    assert score.decomposition_accuracy == 1.0


# --------------------------------------------------------------------------
# Wiring — the helper the pipeline never actually calls
# --------------------------------------------------------------------------


def test_scoring_goes_through_the_shared_benchmark_path(monkeypatch):
    """The cases are scored by `benchmark/scoring.py::score_case`, not by a
    second scorer written for this task."""
    import acceptance.benchmark.hooks as hooks

    calls = []
    original = hooks.score_case

    def spy(case, client=None):
        calls.append(case.case_id)
        return original(case, client)

    monkeypatch.setattr(hooks, "score_case", spy)
    _scored(CASE_DIRS[0], "faithful")
    assert calls == [CASE_DIRS[0].name]


def test_open_questions_reach_the_scored_review():
    """`decompose_case` used to build its Review without them, so every
    open-question metric would have read an empty list and agreed with a
    decomposer that raised none."""
    scored = _scored(CASES_DIR / "189-gate1-run1", "faithful")
    assert [q.id for q in scored.reviewer_output.open_questions] == ["report-format"]


def test_a_case_naming_a_missing_run_fails_rather_than_skipping(tmp_path):
    """A case that quietly skips itself lets the suite shrink without anyone
    noticing — the decompose analogue of #190's unresolvable-revision rule."""
    case_dir = tmp_path / "gone"
    case_dir.mkdir()
    (case_dir / "case.json").write_text(
        json.dumps(
            {
                "run": "189-gate1-run99",
                "run_dir": "tests/fixtures/decompose-stability/189-gate1-run99",
                "judgement": "n/a",
                "summary": "n/a",
            }
        )
    )
    (case_dir / "labels.json").write_text(json.dumps(_labels(CASE_DIRS[0])))
    with pytest.raises(MissingRunInputError) as excinfo:
        build_decompose_case(case_dir, REPO)
    assert "189-gate1-run99" in str(excinfo.value)


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=lambda p: p.name)
def test_a_case_reads_its_task_file_from_the_run_rather_than_a_copy(case_dir):
    """No task text is copied into the case: the run directory is the evidence
    record, and a second copy could drift from it."""
    assert not (case_dir / "current-task.md").exists()
    meta = load_decompose_meta(case_dir)
    assert (REPO / meta.run_dir / "current-task.md").is_file()


def test_the_cases_issue_no_live_model_calls(monkeypatch):
    """Scoring a case never reaches the provider.

    The decomposers run in RECORD mode — an injected `completion_fn` is only
    reached on the live path — which reads like a live call and is not one.
    That is exactly the arrangement worth pinning: it stays correct only while
    every client the suite builds carries its own `completion_fn`, and nothing
    but this test would notice one that stopped.

    `_default_completion_fn` is the single door to litellm (`llm.py`), so
    breaking it is sufficient.
    """
    import acceptance.llm as llm

    def forbidden(**kwargs):
        raise AssertionError("the suite reached the live provider path")

    monkeypatch.setattr(llm, "_default_completion_fn", forbidden)
    for behaviour in ("faithful", "lossy", "permissive"):
        score_case(_scored(CASE_DIRS[0], behaviour))


def test_the_corpus_readme_no_longer_claims_it_is_unread():
    """The old blanket claim is gone, and what replaced it is precise.

    Both halves matter. A README that adds a coverage table while leaving "Not
    yet read by any test" standing above it is worse than one that says nothing,
    because the two statements contradict each other and a reader has no way to
    tell which is current.

    Asserting the absence of a string is normally self-referential — the
    assertion contains the string it searches for — but the subject here is the
    README, a different file, so the check is real.
    """
    readme = (CORPUS_DIR / "README.md").read_text()
    assert "Not yet read by any test" not in readme
    assert "tests/benchmark/test_decompose_regression.py" in readme
    # The parts that remain unread are named rather than left to inference.
    for unread in ("decompose-output.log", "task-diffs.txt", "prediction.md"):
        assert unread in readme


def test_the_corpus_runs_are_all_represented():
    """Seven corpus runs plus this task's own Gate 1 run. A case set that
    silently lost one would still pass every other test in this file."""
    represented = {load_decompose_meta(d).run for d in CASE_DIRS}
    corpus_runs = {p.name for p in CORPUS_DIR.iterdir() if p.is_dir()}
    assert corpus_runs <= represented
    assert "195-gate1-run1" in represented
