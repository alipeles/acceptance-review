# Task
Every claim we hold about evidence-judgement instability is a hand-judged
anecdote that cost a full `check` run plus a manual verdict on each finding. The
discrimination stage is about to change, and nothing today can tell us whether
that change helped.

Build a harness that runs the review pipeline over one input repeatedly, across a
chosen set of models, and reports how much the resulting evidence judgements
move. It measures three sources of movement separately — resampling the same
request, perturbing the request in a way that is irrelevant to the obligation
being watched, and swapping the model — because they are different defects and
one blended figure would hide all three.

The harness reports. It does not decide whether a figure is acceptable; that
belongs to the task that changes the judge.

## Constraints
- Variance is measured across draws that are genuinely independent. A replayed
  response is a recording, so a measurement taken over replayed draws measures
  the recording rather than the judge.
- The statistics come from the variance path the benchmark harness already has,
  `benchmark/scoring.py::disclose_variance`, rather than a second one written for
  this task.

## Scope exclusions
- Changing how any evidence judgement is produced. This task measures; the judge
  is untouched.
- Running the harness automatically, in CI or on a schedule. It issues live model
  calls and is invoked deliberately.
- Interpreting the figures it produces, setting a threshold a rating must meet,
  or reducing the variance it finds.

## Completion expectations
- Implementation
- The caller supplies the input under measurement, the set of models, the number
  of runs per model, and the perturbation to apply. Each has a default, and the
  defaults together are cheap enough to run without first deciding a budget.
- For one input, the harness reports the distribution of evidence classes per
  obligation across the configured runs, separately for each model.
- The harness reports the distribution of each plausible defect's discrimination
  verdict, not only the obligation's final evidence class.
- Perturbation sensitivity is reported as its own figure: the proportion of
  obligations whose evidence class changed under the stated perturbation.
- Cross-model agreement per obligation is reported alongside within-model
  variance.
- The report records the input, the model set, the run count and the seeds that
  produced it, so that a later measurement can be compared against it.
- A run of the harness writes nothing into the repository under review.
