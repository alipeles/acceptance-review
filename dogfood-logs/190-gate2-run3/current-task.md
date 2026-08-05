# Task
The rating-stability corpus at `tests/fixtures/rating-stability/` records what
`acceptance check` concluded across six dogfood runs, and what each conclusion
was judged to be worth at the time. Its README says the corpus is not currently
read by any test. Until those judgements are assertions, every candidate fix to
the evidence-judgement stage is accepted or rejected by eyeball, and the
load-bearing criterion in `docs/DR-180-evidence-judgement-instability.md` — that
`strongly supported` is not issued on evidence that does not earn it — has no
scoreboard.

Turn the corpus into regression cases the benchmark can score.

Each run's input survives. The corpus holds the exact `current-task.md` the run
was given, and `revisions.txt` names the commit it judged; those commits are
still reachable in this repository's history. A case therefore supplies the real
input rather than a reconstruction of it.

What the corpus does not hold is the model's own responses. `check-output.log` is
the rendered report, downstream of them, so the runs cannot be replayed and the
judgement a case is scored under is supplied by the test rather than recorded.

## Ground truth from the corpus
These three lists are the ground truth this task encodes. Each entry names the
run whose `judgement.md` establishes it.

**Ratings that were issued as `strongly supported` on evidence that did not earn
them.** Five obligations, seven run-instances:

| obligation | unearned at | corrected by |
|---|---|---|
| `default-to-most-recent-review` | run 1 | run 2 |
| `no-speculative-writing` | runs 1 and 2 | run 3 |
| `remove-stale-next-instruction-file` | runs 1 and 2 | run 3 |
| `spec-no-longer-describes-written-file` | run 1 | run 3 |
| `retrieve-from-stored-review-state` | run 1 | run 2 |

**Gaps the corpus confirms were real, which a fix must not blunt away.** Seven
strictly real, plus one the corpus records as only partly real:

| obligation | found at | note |
|---|---|---|
| `fixed-command-surface` | run 1 | |
| `default-to-most-recent-review` | run 2 | |
| `retrieve-from-stored-review-state` | run 2 | |
| `remove-stale-next-instruction-file` | run 3 | the silent `--json` deletion |
| `no-speculative-writing` | run 3 | |
| `spec-no-longer-describes-written-file` | run 3 | |
| `preserve-prose-structured-fields` | run 4 | |
| `replace-written-file-with-command` | run 1 | partly real: only its *defaulting to JSON* clause |

**Judgements that were written wrong and rewritten**, where the corpus preserves
both readings. The corrected reading is ground truth in each:

| run | corrected reading |
|---|---|
| run 3 | all three findings were real; the original reading called them tool defects |
| run 5 | the `partially supported` rating was a wrong verdict; run 4's `strongly supported` is correct |

## Constraints
- Cases are scored through the benchmark scoring path the repository already has,
  `benchmark/scoring.py::score_case`, rather than a second one written for this
  task.
- Ground-truth labels use the existing `benchmark/case.py::GroundTruthLabels`
  shape that `tests/fixtures/archetypes/` already carries.
- A case's inputs are the corpus's own `current-task.md` and the base and head
  revisions the run judged. No source file is copied into the case.
- The tree a case is analysed over is the tree at the revision that case judged,
  not the current working tree.
- A revision a case names that no longer resolves fails that case, naming the run,
  rather than silently skipping it.
- Cases issue no live model calls, and no recorded model transcript is committed.
- Each case's ground-truth label is traceable to the `judgement.md` it was
  derived from.

## Scope exclusions
- Changing how any judgement is produced. This task builds the scoreboard; the
  evidence-judgement stage itself is untouched.
- Reducing the instability the corpus documents.
- Setting a threshold that a variance figure or an accuracy figure must meet.
- Rebuilding the corpus runs that establish none of the ground truth above.
- The decompose-stability corpus at `tests/fixtures/decompose-stability/`, which
  is a separate task.
- Modifying any file under `tests/fixtures/rating-stability/` other than its
  README. The corpus is the evidence record these assertions are derived from,
  and editing it to suit a test destroys the thing being tested against.
- Restoring the stored review state that the incremental re-run path (M7.5)
  carried forward into runs 2 and 3. A case supplies the run's input, not the
  state the run resumed from.

## Completion expectations
- Implementation
- Regression cases derived from the corpus are committed as test fixtures.
- A judge that always issues `strongly supported` fails the suite.
- A judge that never issues `strongly supported` fails the suite.
- Every gap listed above as real is required by the suite to still be reported.
- Every rating listed above as unearned is required by the suite to no longer be
  issued.
- Each case derived from run 3 or run 5 records which of the two preserved
  readings in its `judgement.md` is ground truth.
- The control case `163-gate2-run1` carries assertions of the same kind as the
  other cases rather than passing trivially.
- The corpus README no longer states that the corpus is not read by any test, or
  else states precisely which parts of it are still not read.
