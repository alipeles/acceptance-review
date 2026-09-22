# Task

The review asks a model, for each defect and each candidate test, whether the
test would catch the defect. A defect counts as covered as soon as one test is
recorded as catching it, so once that has happened, asking about the defect's
remaining tests cannot change how the defect is rated. The review should stop
paying for those questions.

Before asking, the review ranks each defect's candidate tests by how similar
the test's source is to the defect's description, using embeddings. It then
asks about a defect's tests in that ranked order, in groups sized to the way
questions are already batched, and stops asking about a defect once the
configured number of its tests have been recorded as catching it. That number
defaults to one.

A defect none of whose tests is recorded as catching it has every one of its
tests asked about.

A pair the review stops before asking about is not answered. The review records
it as unjudged, with a cause naming the pair's rank and the tests that had
already covered the defect. Such a pair never counts toward a defect's unknown
pairs, and it cannot move how the defect is rated in either direction. That
cause can only exist on a defect that already has the configured number of
catching tests.

The report says, for each defect, how many of its pairs were asked about and
how many were skipped by stopping early.

Ranking and stopping can be turned off, so a review can still be run the way it
runs today.

## Constraints
- The embedding calls are recorded and replayed like every other model call, so
  two runs over the same input produce identical results.
- The question put to the model does not change. Nothing about the ranking, a
  test's rank, or whether other tests have already caught the defect reaches the
  model.
- This works on whatever pairs are left after the review has already set pairs
  aside for other reasons, such as what the project's tests did under an injected
  edit.

## Scope exclusions
- Changing what is sent in an embedding request.
- Skipping pairs of a defect that no test has caught, by rank or by any other
  cheaper check.
- Changing which tests are candidates for a defect.
