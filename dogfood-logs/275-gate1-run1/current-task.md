# Task
When the stage that prescribes tests returns no prescription for a criterion it
was asked about, the review still completes and reports that criterion's
prescription as one that was not obtained.

## Constraints
- A response that omits one or more of the criteria the prescribing stage was
  asked about does not end the review.
- A review whose prescribing stage omitted a criterion still produces a report
  and a verdict.
- The prescriptions returned for the other criteria in that same response are
  kept.
- Every criterion the prescribing stage was asked about is present in the
  persisted review state, either with a prescribed test or as a prescription
  that was not obtained.
- A criterion whose prescription was not obtained is distinguishable in the
  persisted review state from a criterion carrying a prescribed test.
- A criterion whose prescription was not obtained is distinguishable from a
  criterion that is owed no test.
- The report states, for a criterion whose prescription was not obtained, that
  no prescription was produced for it.
- The report renders that differently from a criterion that is owed no test.
- A criterion whose prescription was not obtained is not rated as strongly
  supported on the test-evidence axis.
- A review containing a criterion whose prescription was not obtained does not
  conclude that no material gaps remain.
- A response naming a criterion the prescribing stage did not ask about is
  rejected.
- A response naming the same criterion more than once is rejected.
- Two runs over the same mandate and the same model responses produce the same
  report.

## Scope exclusions
- Whether the stage asks the model again for the criteria it omitted.
- How many criteria are carried in one request to the model.
- Why the model omits a criterion.
- Which criteria are owed a test at all.
- How a criterion's existing test evidence is rated.
- What the other stages do when their own responses omit a criterion.

## Completion expectations
- Implementation
- A test drives the prescribing stage with a response that omits a criterion it
  was given, and asserts the stage returns rather than raising.
- A test asserts that the prescriptions for the criteria that response did
  answer are kept.
- A test asserts that the omitted criterion is present in the persisted review
  state as a prescription that was not obtained.
- A test asserts that a prescription that was not obtained is distinguishable
  in the persisted review state from a prescribed test.
- A test asserts that a review whose prescribing stage omitted a criterion
  produces a report.
- A test asserts that the report states no prescription was produced for the
  omitted criterion.
- A test asserts that the report renders that differently from a criterion that
  is owed no test.
- A test asserts that a criterion whose prescription was not obtained is not
  rated strongly supported on the test-evidence axis.
- A test asserts that a review containing such a criterion does not conclude
  that no material gaps remain.
- A test asserts that a response naming a criterion the stage did not ask about
  is rejected.
- A test asserts that a response naming the same criterion more than once is
  rejected.
- A test asserts that two runs over the same mandate and the same model
  responses produce the same report.
