# Task
A review completes and reports even when some of its criteria are ones no test
could ever evidence.

## Constraints
- A test recommendation may state that no test can evidence its criterion.
- A statement that no test can evidence a criterion carries a reason.
- A criterion answered with such a statement does not abort the review.
- A criterion for which the model returns neither a recommendation nor such a
  statement still aborts the review.
- A statement that no test can evidence a criterion is recorded in the persisted
  review state.
- A recorded statement of that kind names the criterion it applies to.
- A review in which every weak criterion is answered that way produces a report.
- A criterion that the change addresses and that carries such a statement is
  classified as indeterminate on the test-evidence axis.
- The report states, for a criterion no test can evidence, that no test can
  evidence it.
- The report makes no such statement for a criterion that merely carries no
  recommendation.
- A review of a change that modifies only configuration files produces a report.
- Two runs over the same criteria and the same change produce the same
  statements that no test can evidence them.
- A recorded model exchange carries the reason the model stopped generating.
- A test whose assertions bear on several criteria is recorded against every one
  of those criteria.
- Criteria that overlap one another are not treated as alternatives when a test
  bears on more than one of them.

## Scope exclusions
- Whether the existing exclusion of criteria whose evidence is code alone is
  folded into the same mechanism.
- How many criteria are carried in one recommendation request.
- Whether the model's judgement that no test can evidence a criterion is
  correct.
- How a criterion's test evidence is classified as weak in the first place.
- How the overall completion verdict is derived for criteria that carry no such
  statement.
- Recommending non-test evidence in place of the test that cannot exist.

## Completion expectations
- Implementation
- A test asserts that a criterion answered with a statement that no test can
  evidence it does not abort the review.
- A test asserts that a criterion the model omits entirely still aborts the
  review.
- A test asserts that such a statement reaches the persisted review state
  attributed to its criterion.
- A test asserts that a review whose weak criteria are all answered that way
  produces a report.
- A test asserts that an addressed criterion carrying such a statement is
  classified indeterminate on the test-evidence axis.
- A test asserts that the report states, for a criterion no test can evidence,
  that no test can evidence it.
- A test asserts that the report makes no such statement for a criterion that
  merely carries no recommendation.
- A test asserts that a review of a change modifying only configuration files
  produces a report.
- A test asserts that two runs over the same criteria and change produce the
  same statements.
- A test asserts that a recorded model exchange carries the reason the model
  stopped generating.
- A test asserts that a test bearing on several criteria is recorded against
  every one of them.
- A test asserts that the mapping instruction requires every overlapping
  criterion to be returned rather than the closest one.
