# Task
Every claim we hold about evidence-judgement instability is a hand-judged
anecdote that cost a full `check` run plus a manual verdict on each finding. The
discrimination stage is about to change, and nothing today can tell us whether
that change helped. Build a harness that runs the review pipeline over a fixed
input repeatedly, across a chosen set of models, and reports how much the
resulting evidence judgements move.

Three sources of movement are measured and reported separately, because they are
different defects and one blended figure would hide all three:

- **resample variance** — the same request drawn N times;
- **perturbation sensitivity** — a change to the request that is semantically
  irrelevant to a given obligation, such as adding a test that maps to a
  different obligation;
- **model sensitivity** — the same input judged by different models.

The harness reports. It does not decide whether a figure is acceptable; that
belongs to the task that changes the judge.

## Constraints
- Variance is measured across draws that are genuinely independent. A replayed
  response is a recording, so a measurement taken over replayed draws measures
  the recording rather than the judge.
- The statistics come from the variance path the benchmark harness already has,
  rather than a second one written for this task.
- A reported measurement states the conditions that produced it — the input, the
  models, the number of runs, the seeds — so that a later measurement can be
  compared against it.
- The number of runs and the set of models are chosen by the caller, and the
  default is cheap enough to run without first deciding a budget.
- The harness leaves no trace in the repository it reviews.

## Scope exclusions
- Changing how any evidence judgement is produced. This task measures; the judge
  is untouched.
- Running the harness automatically, in CI or on a schedule. It issues live model
  calls and is invoked deliberately.
- Interpreting the figures it produces, or setting a threshold a rating must meet.
- Reducing the variance it finds.

## Completion expectations
- Implementation
- For one fixed input, the harness reports the distribution of evidence classes
  per obligation across N runs, separately for each model.
- The harness reports the distribution of each plausible defect's discrimination
  verdict, not only the obligation's final evidence class.
- Perturbation sensitivity is reported as its own figure: given a stated
  irrelevant perturbation, the proportion of obligations whose evidence class
  changed.
- Cross-model agreement per obligation is reported alongside within-model
  variance.
- The report records the input, the model set, the run count and the seeds that
  produced it.
- The run count and the model set are supplied by the caller and have a default.
- A run of the harness writes nothing into the repository under review.
