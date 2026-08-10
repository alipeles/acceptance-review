# Task
The completion verdict accounts for how much of the mandate the review actually
covered, so a review that spoke to only part of the mandate cannot report that
it found no material gaps.

## Constraints
- The share of the mandate's requirements that produced at least one obligation
  is recorded on the completion result.
- A requirement that produced no obligation lowers the recorded share.
- A review whose recorded share is short of the whole mandate is never reported
  as free of material gaps.
- A share short of the whole mandate only ever bounds the verdict and never
  raises it, so a review that covers less of the mandate never reports a better
  result than the same review covering more of it.
- A requirement that states no checkable expectation does not lower the recorded
  share.
- Task-file text that produced no requirement at all bounds the verdict in the
  same way as a requirement that produced no obligation.
- The completion verdict states the share it was derived under and names the
  requirements that produced nothing.
- The completion verdict is derived from the review's own recorded state without
  consulting a model.
- Two runs over byte-identical task text produce byte-identical review state.
- Tests issue no live model calls.

## Scope exclusions
- Whether a requirement that produced no obligation was correctly declined; the
  stated reason is taken at face value and not re-judged.
- How stable decomposition is from one run to the next, which is #193.
- Measuring how accurate decomposition is, which is #211.
- How finely a single requirement is split into obligations, which is #117.
- Whether obligation identifiers are stable across task-file edits, which is
  #231.
- How an obligation's evidence is rated, which is #180.
- Which tests are discovered, and which obligations they are mapped to.

## Completion expectations
- Implementation
- A test asserts that two reviews with identical obligation-level evidence and a
  different share of the mandate covered do not produce the same completion
  result.
- A test asserts that a review in which a requirement produced no obligation is
  not reported as free of material gaps.
- A test asserts that a requirement stating no checkable expectation does not
  lower the recorded share.
- A test asserts that a review covering less of the mandate never reports a
  better result than the same review covering more of it.
- A test asserts that the verdict is derived with the mandate's requirements in
  hand, by the same path a review run takes.
- A test asserts that two runs over byte-identical task text produce
  byte-identical review state.
