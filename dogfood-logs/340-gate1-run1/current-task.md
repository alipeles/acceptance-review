# Task

The review already runs the project's candidate tests against each edit it
injects, and then uses the result for nothing unless the edit was separately
checked. Checking is off, so on a normal review the result is used for nothing at
all, and every combination of a plausible defect and a candidate test is still
put to a model. Those calls are almost all of what a review costs, and the answer
comes back "this test would not catch it" nearly every time.

Let the run choose which of those questions are worth asking. When at least one
candidate test failed under an edit, that edit demonstrably changed what the code
does, so a test that went on passing under it is not sensitive to the change and
is not asked about. The tests that failed under the same edit are still asked
about, because a test going red does not on its own say the named defect is what
it caught.

When no candidate test failed under an edit, nothing was demonstrated: an edit
that changed nothing and an edit that changed something no test watches look
alike from outside. Every pair for that defect is asked about, exactly as if no
edit had been built. A defect for which no edit could be built is asked about as
it is today.

A pair dropped this way has not been decided, and must not read as though it had
been. It is recorded with the reason it was dropped and the injection attempt the
decision rests on, so a reader can see it was skipped rather than answered, and
it is not a demonstration that the test fails to catch the defect.

Whether running the project's tests is worth doing is the review's own decision,
and that decision has to account for this. Until now nothing consumed the run
unless edits were checked, and the review declined to run on that ground.
Choosing which questions to ask is a second thing the run earns.

Dropping pairs can be turned off, so a review can still be run the way it runs
today.

For each defect the stage was asked about, the report says how many of its pairs
the run itself decided, how many were asked of the model, and how many were
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
