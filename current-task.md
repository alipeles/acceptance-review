# Task

For a named plausible defect, the review builds the smallest edit that makes that
defect true, applies it to a throwaway copy of the code, and runs the project's
candidate tests against that copy. A test that fails is shown to discriminate for
that defect, and one such test is enough: no second test has to agree, and a
defect one test fails on is covered. That holds for a failure the edit caused; a
failure the edit could not have caused, because the edit was refused or because
it broke something other than the behaviour named, says nothing either way.
When no test fails, the candidate tests are shown not to discriminate for it.
Either way the conclusion is an observation rather than a prediction, and is
recorded at the strongest evidence tier the review produces on its own.

The injected text is recorded next to the result, so a reader who disagrees with
what was injected can see exactly what it was.

Whether running the project's tests is worth doing is the review's own decision.
Nobody is asked to switch it on: the review runs them when something will use the
result, does not run them otherwise, and says which it chose and why.

When it does run them, it runs them once against the code as delivered before
altering anything. A test that already fails there tells nothing when it fails
later, so this run is what makes the later result mean anything. Such a test is
set aside: it takes no part in any conclusion, and the report names it. One test
that cannot be trusted does not stop the others from running, and does not stop
the review.

The existing judgement that reads code without running it does not go away, and
does not run first. It runs on what execution could not settle: a defect no edit
could express, a defect whose edit could not be built, and every defect at all
when the code cannot be run. Where nothing can be run, the review reaches the
conclusions it reaches today, and in that case — and only in that case — its
evidence stays at the weaker tier.

A defect execution did not settle carries the reason it did not.

## Constraints
- The edit replaces one continuous stretch of a single file, within a region the
  defect names. A defect naming no region cannot be edited, and says so.
- A file that has a parser must still parse after the edit. A file with no parser
  is not invalid for lacking one — a requirement can be stated in prose and
  broken in prose, and the tests that read that prose are the ones that catch it.
- Whether an edit is valid is settled by mechanical checks alone.

## Scope exclusions
- Deciding whether a project's tests can be run at all, and which of them are
  candidates.
- Recording which lines of code a test executed.
- Writing or altering a test so that a defect can be reached.
- Running the project's whole test suite.
