# Task
When the review records, for each recorded way of failing and each candidate
test, whether that test would fail if the delivered code contained that way of
failing, it obtains a short reason only where the test would fail.

## Constraints
- What the review obtains about a pair where the test would fail is which pair it
  is, that it would fail, and a short reason.
- What the review obtains about a pair where the test would not fail is which
  pair it is and that it would not fail, and nothing else.
- Which of the two an answer is, is settled by the verdict the answer carries,
  not by which fields happen to be present in it. An answer that reports the test
  would not fail and carries a reason anyway is not a verdict the review accepts.
- An answer that reports the test would fail and carries no reason is not a
  verdict the review accepts.
- An answer the review does not accept leaves its pair recorded as unjudged,
  naming the way of failing, the test, and why, exactly as a pair the judge never
  answered about is.
- Both kinds of answer are asked for in the same request as each other.
- A verdict the review keeps about a pair where the test would not fail carries
  no reason where it is stored.
- Which pairs the review judges is unchanged.
- The conditions under which the review reuses a verdict rather than producing it
  again are unchanged.
- Whether the review reports the work complete, every rating it gives a
  criterion, and every test it recommends are unchanged.

## Scope exclusions
- Which ways of failing the review records, and how it produces them.
- Deriving a criterion's rating, the completion conclusion, or any recommended
  test from judged pairs.
- What the review shows a reader about a pair it has judged.
- How pairs are grouped into requests, and the limit on how many judgements one
  request asks for.
- Running the delivered code or any test.

## Completion expectations
- Implementation.
- A test reads the shape of the request as it is sent and fails if that shape
  permits a reason on a pair where the test would not fail.
- A test fails when an answer reporting that the test would fail carries no
  reason and is nonetheless kept as a verdict.
- A test fails when an answer reporting that the test would not fail carries a
  reason and is nonetheless kept as a verdict.
- A test asserts that a pair whose answer the review does not accept is recorded
  as unjudged, naming the way of failing, the test and the cause.
- A test asserts that a stored verdict about a pair where the test would not fail
  carries no reason.
- A test asserts that adding one candidate test between two continued runs
  produces new verdicts only for pairs concerning that test.
- Two recorded runs over the same input produce byte-identical review state and
  byte-identical report output.
