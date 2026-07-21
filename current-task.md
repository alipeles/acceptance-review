# Task
Convert the parsed task file into discrete, typed obligations the checker can review the implementation against.

## Constraints
- Type each obligation using the §7.3 set: functional, boundary, error-handling, invariant, regression, compatibility, explanation/observability, docs/config, human-review.
- Give each obligation a stable id and link it to the source span in the task text it derives from.
- Produce obligations through a schema-constrained model call recorded for replay; capability tests run off the recorded transcript with no live calls.

## Completion expectations
- Implementation
- Unit tests
