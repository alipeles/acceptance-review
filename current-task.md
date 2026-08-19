# Task
Each criterion records which kinds of evidence it requires, and only the stages
that gather those kinds of evidence consider it.

## Constraints
- Each criterion records which kinds of evidence it requires.
- The kinds recorded are exactly one of: both code and test evidence, code
  evidence alone, test evidence alone, or neither.
- A criterion cannot record that test evidence is both required and not
  required.
- The kinds a criterion requires are decided when criteria are derived from the
  mandate.
- No later stage revises the kinds a criterion requires.
- A criterion requires both kinds of evidence unless a reason is given for
  requiring fewer.
- A criterion requiring fewer than both kinds carries the reason it does.
- The recorded kinds are part of the persisted review state.
- A criterion that does not require test evidence is not offered to the stage
  that matches tests to criteria.
- A criterion that does not require test evidence is not rated on the
  test-evidence axis.
- A criterion that does not require test evidence is not prescribed a test.
- A criterion that does not require code evidence is not offered to the stage
  that classifies whether the change addresses it.
- A criterion requiring neither kind is reported as needing evidence the review
  cannot gather.
- A criterion the change addresses and that requires code evidence alone is
  reported as satisfied rather than as unmeasured.
- A criterion under a mandate's scope-exclusion heading may still require test
  evidence.
- A review of a change that modifies only configuration files produces a report.
- Two runs over the same mandate record the same required kinds.
- The report states, for a criterion that does not require test evidence, that
  test evidence is not required, and why.
- The report distinguishes that from a criterion that requires test evidence and
  has none.
- A recorded model exchange carries the reason the model stopped generating.
- A test whose assertions bear on several criteria is recorded against every one
  of those criteria.
- Criteria that overlap one another are not treated as alternatives when a test
  bears on more than one of them.

## Scope exclusions
- How many criteria are carried in one request to the model.
- Whether the model's judgement about which kinds a criterion requires is
  correct.
- How a criterion's test evidence is rated once the test-evidence axis applies.
- Which evidence tier a finding is recorded at.
- How the mandate is parsed into its sections.

## Completion expectations
- Implementation
- A test asserts that the kinds of evidence a criterion requires reach the
  persisted review state.
- A test asserts that a criterion requiring fewer than both kinds carries a
  reason.
- A test asserts that a criterion with no stated reason requires both kinds.
- A test asserts that a criterion not requiring test evidence is absent from the
  input to the stage that matches tests to criteria.
- A test asserts that a criterion not requiring test evidence is left unrated on
  the test-evidence axis.
- A test asserts that a criterion not requiring test evidence is prescribed no
  test.
- A test asserts that a criterion not requiring code evidence is absent from the
  input to the stage that classifies whether the change addresses it.
- A test asserts that a criterion requiring neither kind is reported as needing
  evidence the review cannot gather.
- A test asserts that an addressed criterion requiring code evidence alone is
  reported as satisfied.
- A test asserts that a criterion under a scope-exclusion heading can require
  test evidence.
- A test asserts that a review of a change modifying only configuration files
  produces a report.
- A test asserts that two runs over the same mandate record the same required
  kinds.
- A test asserts that the report states why test evidence is not required for a
  criterion that does not require it.
- A test asserts that the report renders that differently from a criterion that
  requires test evidence and has none.
- A test asserts that a recorded model exchange carries the reason the model
  stopped generating.
- A test asserts that a test bearing on several criteria is recorded against
  every one of them.
- A test asserts that the mapping instruction requires every overlapping
  criterion to be returned rather than the closest one.
