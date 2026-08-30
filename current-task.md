# Task
For each way of failing that the review has recorded against a criterion, and
each candidate test, the review records whether that test would fail if the
delivered code contained that way of failing.

## Constraints
- A pair is one recorded way of failing and one candidate test. Every pair is
  judged unless a path from that test to the source regions the way of failing
  implicates is proved absent. A pair whose path cannot be settled either way is
  judged.
- Every pair left unjudged is recorded, naming the way of failing, the test, and
  why it was not judged, and the review reports those records.
- The question put about a judged pair is whether that test would fail if the
  delivered code contained that way of failing.
- Pairs are judged in groups, and no group asks for more judgements in one
  request than a fixed limit allows.
- What comes back about a judged pair is which pair it is, its verdict, and a
  short reason, and nothing further.
- A verdict is reused rather than produced again exactly while both the way of
  failing it concerns and the source of the test it concerns are unchanged.
- A verdict whose way of failing changed, or whose test's source changed, is
  produced again.
- A run continuing an earlier run reuses every verdict it is entitled to reuse.
- A run continuing an earlier run produces again only the verdicts it is not
  entitled to reuse.
- Where a verdict was reused rather than produced again, the review says so.
- Whether the review reports the work complete, every rating it gives a
  criterion, and every test it recommends are what they would be if no pair had
  been judged at all.
- The review reports, for each criterion, the support its judged pairs imply
  beside the rating the review gives that criterion today, and names the
  criteria where the two disagree.

## Scope exclusions
- Producing the ways of failing that pairs are judged against.
- Deriving a criterion's rating, the completion conclusion, or any recommended
  test from judged pairs.
- Resolving a name to its definition, or following references beyond a single
  step, in order to decide whether a path is absent.
- Which criteria the review derives from the mandate, and how it derives them.
- How the review gathers, maps, judges or rates test evidence today, and
  retiring any part of it.
- Selecting the shape of the request that carries the pair question at run
  time. The shape is fixed in the software; nothing chooses between candidates
  while a review runs.
- Running the delivered code or any test.

## Completion expectations
- Implementation.
- A test fails when a pair whose path cannot be settled either way is left
  unjudged rather than judged.
- A test fails when a pair is left unjudged without a record naming the way of
  failing, the test and the reason.
- A test asserts that adding one candidate test between two continued runs
  produces new verdicts only for pairs concerning that test.
- A test fails when a verdict is produced again across two continued runs
  although its way of failing and its test's source are both unchanged.
- A test fails when a verdict is reused although its test's source changed.
- A test fails when judging pairs changes the review's completion conclusion,
  any criterion's rating, or which tests it recommends.
- A test asserts the report shows, for each criterion, the support its judged
  pairs imply beside the rating the review gives that criterion today.
- Two recorded runs over the same input produce byte-identical review state and
  byte-identical report output.
