# Task

The review injects an edit for each plausible defect it enumerates and runs the
project's candidate tests against that edit. It must use what that run showed to
decide which defect-and-test pairs are worth putting to a model, so that the
model is asked far fewer of those questions than it is asked today.

Where at least one candidate test failed under an edit, a test that went on
passing under the same edit is not put to the model. The tests that failed under
it are still put to the model, because a test going red does not on its own say
the named defect is what it caught.

Where no candidate test failed under an edit, every pair for that defect is put
to the model, as is every pair for a defect no edit could be built for.

A pair the review drops this way has not been decided, and must not read as
though it had been. The review records, for each dropped pair, why it was dropped
and which injection attempt the decision rests on. A dropped pair is not a
demonstration that the test fails to catch the defect.

A run of the project's tests that would let the review drop pairs is worth doing
on that ground alone.

Dropping pairs can be turned off, so a review can still be run the way it runs
today.

For each defect the stage was asked about, the report says how many of its pairs
the run itself decided, how many were put to the model, and how many were
dropped.

## Constraints
- Nothing about the edit, or about what the tests did under it, reaches the
  model.
- An edit nobody checked still settles nothing. A dropped pair reaches no
  evidence tier and yields no finding.

## Scope exclusions
- Checking whether an edit really makes its named defect true.
- Building an edit, choosing the region it falls in, or deciding whether it is
  valid.
- Which tests are candidates, and whether the project's tests can be run at all.
- Running the project's whole test suite.
