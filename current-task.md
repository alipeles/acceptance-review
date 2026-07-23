# Task
Score unrequested-change detection as its own precision/recall pair on the code→obligation axis, separate from the gap metric (DR-081 decision 1).

## Constraints
- Ground truth: obligation-less unrequested-change entries matched against obligation-less findings; do not attempt to link them to obligations.
- Report the metric separately from `gap_recall`/`gap_precision`, never folded into it.
- Update archetype #8's ground truth.
- Detection stays recall-forward; precision is reported, not optimized against.
- Archetype layer only in Stage 1; real-change scoring is deferred (DR-081).

## Completion expectations
- Implementation
- Unit tests: archetype #8 contributes an `unrequested_precision`/`unrequested_recall` number that does not route through its `leave-existing` obligation's coverage classification.
