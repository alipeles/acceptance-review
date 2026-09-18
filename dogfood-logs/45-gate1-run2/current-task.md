# Task

For a named plausible defect, the review builds the smallest edit that makes that
defect true, applies it to a throwaway copy of the code, and runs the project's
candidate tests against the altered copy. A test that fails is shown to
discriminate for that defect. When no test fails, the candidate tests are shown
not to discriminate for it. Either way the conclusion is an observation rather
than a prediction, and is recorded at the strongest evidence tier the review
produces on its own.

The injected text is recorded next to the result, so a reader who disagrees with
what was injected can see exactly what it was.

Before anything is altered, the candidate tests run once against the code as
delivered. A test that already fails there tells nothing when it fails later, so
this run is what makes the later result mean anything. If any candidate test
fails on the delivered code, the review stops and says why. A project can be
configured to continue anyway, for a failure its owners have chosen to live with;
then the failing tests take no part in any conclusion, and the report says which
ones were set aside.

The existing judgement that reads code without running it does not go away, and
does not run first. It runs on what execution could not settle: a defect no edit
could express, a defect whose edit could not be built, and every defect at all
when the code cannot be run. A review where nothing can be run reaches the
conclusions it reaches today, with its evidence recorded at the weaker tier.

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
