# Task
The decompose-stability corpus at `tests/fixtures/decompose-stability/` records
what `acceptance decompose` produced across seven consecutive Gate 1 runs for
#189, and what each run's breakdown was judged to be worth at the time. Its
README says the corpus is not yet read by any test. Until those judgements are
assertions, every candidate fix to the decomposition stage is accepted or
rejected by eyeball — and this is the corpus where eyeballing already failed
twice, in writing.

Turn the corpus into regression cases the benchmark can score.

Each run's input survives exactly. `decompose` takes a task file and nothing
else, and all seven `current-task.md` files are committed. A case therefore
supplies the real input rather than a reconstruction of it. What the corpus does
not hold is the model's own responses: `decompose-output.log` is the rendered
breakdown, downstream of them, so the runs cannot be replayed, and the judgement
a case is scored under is supplied by the test rather than recorded.

The task files are not byte-identical across runs; `task-diffs.txt` holds the
exact edit between each consecutive pair. Each assertion therefore binds to its
own run's task file, and what this suite produces is per-run content-quality
cases rather than stability cases.

## Ground truth from the corpus
The tables below are the ground truth this task encodes. Each entry names the run
whose `judgement.md` establishes it.

### Content that was lost
A requirement, an open question, or a symbol present in the task file and absent
from the breakdown produced over it. This is the serious class.

| lost | lost at | recovered at | established by |
|---|---|---|---|
| the open-questions half of the compound decomposition-variance requirement | run 4 | run 5 | run 4, Finding 1 |
| the scope exclusion *"interpreting the figures it produces, setting a threshold a rating must meet, or reducing the variance it finds"* | run 6 | run 7 | run 7, Finding 1 |
| the `output format` open question | runs 3, 4 and 7 | runs 5 and 6 | run 5, *The confirming observation* |
| the symbol `benchmark/scoring.py::disclose_variance` from the obligation derived from the text naming it | run 4 | — | run 4, Finding 2 |
| the symbol `align_obligations` from the obligation derived from the text naming it | run 4 | — | run 4, Finding 2 |

The `output format` question is the one entry whose defect is its *absence* rather
than its presence: no version of the task file says anything about output format,
so the question is never answered and its disappearance is a drop.

### Obligation types the corpus establishes as wrong
Three prohibitions on the harness's own behaviour, each statically checkable, all
typed `human_review` (run 7, Finding 2):

| obligation | text |
|---|---|
| `no-acceptability-threshold` | *Leave acceptability decisions to the task that changes the judge.* |
| `no-threshold-or-rating` | *Keep threshold-setting and rating interpretation out of the harness.* |
| `no-variance-reduction` | *Preserve the measured variance without attempting to reduce it.* |

### One obligation re-typed on unchanged source text
`record-run-provenance` was typed `invariant` in runs 3 and 4, `docs_config` in
run 5, `functional` in run 7 (run 5 *Secondary finding*; run 7, Finding 2). The
ground truth is that one obligation derived from unchanged text carries one type
across those runs. Which of the three types is correct is not established by the
corpus.

### Shape differences, which are not defects
The same content partitioned differently. Both directions occur:

| runs | difference | established by |
|---|---|---|
| 3 → 4 | one obligation, `harness-runs-review-pipeline-repeatedly`, became three from an unchanged sentence | run 4, *Prediction 1* |
| 5 → 6 | two obligation pairs were each bundled into one, from unchanged text | run 6, *Prediction 1* |

### Judgements that were written wrong and corrected
The corpus preserves both readings. The corrected reading is ground truth in each.

| run | corrected reading |
|---|---|
| run 4 | the two open questions were dropped, not resolved; the original judgement leaned toward genuine resolution and run 5 falsified it by bringing both back |
| run 6 | the breakdown was not accurate; a whole scope exclusion produced no obligation, and the correction written after run 7 stands above the original wording |

## Ground truth from this task's own Gate 1 run
An eighth case derives from `dogfood-logs/195-gate1-run1/`, the Gate 1 run for
this task. It is the strongest case in the suite: its task file was authored
knowing what the decomposition should contain, so the losses are enumerated
rather than reconstructed. Its `judgement.md` establishes the following.

**Requirements that produced no obligation.** Four Completion expectations:

| requirement |
|---|
| *A decomposer that drops content fails the suite.* |
| *A decomposer that raises every open question fails the suite.* |
| *A decomposer that splits every sentence into its own obligation fails the suite.* |
| *Every case carries assertions of the same kind as the other cases rather than passing trivially.* |

And five Scope exclusions:

| requirement |
|---|
| *Deciding which of its three observed types `record-run-provenance` should carry.* |
| *Measuring resample variance over one unchanged task file, which is #189's harness.* |
| *Producing new corpus runs by re-running `decompose`.* |
| *The rating-stability corpus and the regression suite over it, which #190 delivered.* |
| *Modifying any file under `tests/fixtures/decompose-stability/` other than its README.* |

**Obligations wrongly typed `human_review`.** Both are statically checkable
prohibitions on the harness's own behaviour:

| obligation |
|---|
| `preserve-no-thresholding` |
| `preserve-no-variance-reduction` |

**Open questions raised that the task file answers.** All three, each answerable
from the task file alone:

| question |
|---|
| `clarify-record-run-provenance-type` |
| `clarify-run-4-reading` |
| `clarify-run-6-reading` |

## Constraints
- Cases are scored through the benchmark scoring path the repository already has,
  `benchmark/scoring.py::score_case`, rather than a second one written for this
  task.
- Ground-truth labels use the existing `benchmark/case.py::GroundTruthLabels`
  shape that `tests/fixtures/archetypes/` already carries.
- A case's input is the `current-task.md` of the run that case derives from.
- No task text is copied into the case.
- Obligation sets are compared through `benchmark/alignment.py::align_obligations`.
- Obligation counts are never compared.
- Content differences are asserted separately from shape differences.
- A shape difference listed above is required by the suite not to count against
  decomposition quality.
- A corpus task file a case names that is missing fails that case, naming the run,
  rather than silently skipping it.
- Cases issue no live model calls.
- No recorded model transcript is committed.
- Each case's ground-truth label is traceable to the `judgement.md` it was derived
  from.

## Scope exclusions
- Changing how any decomposition is produced. This task builds the scoreboard;
  the decomposition stage itself is untouched.
- Reducing the instability the corpus documents.
- Setting a threshold that a variance figure or an accuracy figure must meet.
- Deciding which of its three observed types `record-run-provenance` should carry.
- Measuring resample variance over one unchanged task file, which is #189's
  harness.
- Producing new corpus runs by re-running `decompose`.
- The rating-stability corpus at `tests/fixtures/rating-stability/` and the
  regression suite over it, which #190 delivered.
- Modifying any file under `tests/fixtures/decompose-stability/` other than its
  README. The corpus is the evidence record these assertions are derived from,
  and editing it to suit a test destroys the thing being tested against.

## Completion expectations
- Implementation
- Regression cases derived from the corpus are committed as test fixtures.
- A decomposer that drops content fails the suite.
- A decomposer that raises every open question fails the suite.
- A decomposer that splits every sentence into its own obligation fails the suite.
- Every content loss listed above is required by the suite to be reported.
- Every obligation listed above as wrongly typed `human_review` is required by the
  suite to carry some other type.
- An obligation derived from task-file text that names a symbol is required by the
  suite to retain that symbol.
- Each case derived from run 4 or run 6 records which of the two preserved
  readings in its `judgement.md` is ground truth.
- A case derived from `dogfood-logs/195-gate1-run1/` requires each requirement
  listed above as producing no obligation to be reported.
- That case requires each open question listed above as answerable from the task
  file to no longer be raised.
- Every case carries assertions of the same kind as the other cases rather than
  passing trivially.
- The corpus README no longer states that the corpus is not read by any test, or
  else states precisely which parts of it are still not read.
