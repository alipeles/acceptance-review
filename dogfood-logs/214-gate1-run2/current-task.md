# Task
The completion verdict accounts for every requirement of the mandate, so a
review cannot report that it found no material gaps while part of the mandate
produced nothing it was able to judge.

## Constraints
- A requirement deliberately declined with a stated reason does not count
  against how much of the mandate the review covered.
- An open question that the change itself answers yields an obligation stating
  the behaviour the change committed to.
- An obligation derived from an answered open question cites the places in the
  change that answer it, and is treated as implemented on the strength of those
  citations rather than being reported as missing.
- An obligation derived from an answered open question is carried on the test
  evidence axis like any other, so a settled implementation choice that no test
  exercises prevents a report of no material gaps.
- An open question the change does not answer yields no obligation.
- Task-file text that yielded no requirement at all prevents a report of no
  material gaps.
- How much of the mandate the review covered is recorded on the completion
  result and stated in the report.
- Covering less than the whole mandate only ever bounds the verdict and never
  raises it, so a review that covers less of the mandate never reports a better
  result than the same review covering more of it.
- The completion verdict is derived from the review's own recorded state without
  consulting a model.
- Two runs over byte-identical task text produce byte-identical review state.
- Tests issue no live model calls.

## Scope exclusions
- Whether a requirement that was deliberately declined was correctly declined;
  the stated reason is taken at face value and not re-judged.
- How an obligation's test evidence is rated once it reaches the rating stage,
  which is #180.
- How stable decomposition is from one run to the next, which is #193.
- Measuring how accurate decomposition is, which is #211.
- How finely a single requirement is split into obligations, which is #117.
- Whether obligation identifiers are stable across task-file edits, which is
  #231.
- Which tests are discovered, and which obligations they are mapped to.

## Completion expectations
- Implementation
- A test asserts that a requirement deliberately declined with a stated reason
  does not count against how much of the mandate the review covered.
- A test asserts that an open question answered by the change yields an
  obligation stating the behaviour the change committed to.
- A test asserts that an obligation derived from an answered open question is
  treated as implemented and cites the places in the change that answer it.
- A test asserts that an obligation derived from an answered open question that
  no test exercises prevents a report of no material gaps.
- A test asserts that an open question the change does not answer yields no
  obligation.
- A test asserts that task-file text yielding no requirement at all prevents a
  report of no material gaps.
- A test asserts that how much of the mandate the review covered is recorded on
  the completion result.
- A test asserts that the verdict is derived with each requirement's disposition
  in hand, by the same path a review run takes.
- A test asserts that two runs over byte-identical task text produce
  byte-identical review state.
