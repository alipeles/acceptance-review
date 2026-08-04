# Task
Every claim we hold about the review's judgement instability is a hand-judged
anecdote that cost a full run plus a manual verdict on each finding. The
discrimination stage is about to change, and nothing today can tell us whether
that change helped.

Build a harness that runs the review pipeline over one input repeatedly, across a
chosen set of models, and reports how much its judgements move. It measures three
sources of movement separately — resampling the same request, perturbing the
request in a way that is irrelevant to the judgement being watched, and swapping
the model — because they are different defects and one blended figure would hide
all three.

The measured surface is the whole pipeline, not only the evidence stages. A Gate 1
run of this very task showed the decompose stage dropping two open questions in
response to an edit that touched neither, so decomposition instability is observed
rather than hypothetical.

The harness reports. It does not decide whether a figure is acceptable; that
belongs to the task that changes the judge.

## Constraints
- Variance is measured across draws that are genuinely independent. A replayed
  response is a recording, so a measurement taken over replayed draws measures
  the recording rather than the judge.
- The statistics come from the variance path the benchmark harness already has,
  `benchmark/scoring.py::disclose_variance`, rather than a second one written for
  this task.
- Obligations are compared across runs by what they say rather than by their
  identifiers, which decompose assigns afresh on every run. The comparison used is
  the existing `benchmark/alignment.py::align_obligations`.

## Scope exclusions
- Changing how any judgement is produced. This task measures; the pipeline is
  untouched.
- Running the harness automatically, in CI or on a schedule. It issues live model
  calls and is invoked deliberately.
- Interpreting the figures it produces, setting a threshold a rating must meet,
  or reducing the variance it finds.

## Completion expectations
- Implementation
- The caller supplies the input under measurement, the set of models, the number
  of runs per model, and the perturbation to apply. Each has a default.
- The default model set is a single model and the default run count is a small
  number, so that measuring more than one model is something the caller opts
  into rather than the cost of a default run.
- For one input, the harness reports the distribution of evidence classes per
  obligation across the configured runs, separately for each model.
- The harness reports the distribution of each plausible defect's discrimination
  verdict, not only the obligation's final evidence class.
- The harness reports which obligations appear in some runs of one task file but
  not others.
- The harness reports which open questions appear in some runs of one task file
  but not others.
- Perturbation sensitivity is reported as its own figure: the proportion of
  watched judgements that changed under the stated perturbation.
- Cross-model agreement per obligation is reported alongside within-model
  variance.
- The report records the input, the model set, the run count and the seeds that
  produced it, so that a later measurement can be compared against it.
- A run of the harness writes nothing into the repository under review.
