# Task
The measurement harness scores the ways of failing that a review recorded
against a human-authored reference set. The figure for what the review failed to
record and the figure for what it wrongly predicted about tests are never
combined into a single figure.

## Constraints
- A reference set states, for each criterion of a labelled case, the ways of
  failing a competent reviewer should record. Each carries an identifier, a
  classification drawn from the same fixed vocabulary the review uses, a
  free-text description, and the tests that would fail if the delivered code
  contained it.
- A criterion for which no way of failing is plausible carries that fact and the
  reason, and stays distinguishable from a criterion the reference set says
  nothing about.
- A reference set naming a criterion its case does not define, or naming a test
  its case does not supply, is rejected rather than loaded.
- A recorded way of failing is matched to a labelled one by what the two
  describe, not by their wording, and each side takes part in at most one match.
- Whether a match was found and whether the two classifications agree are
  reported as separate figures.
- The share of recorded ways of failing carrying the vocabulary's escape value is
  reported as a standing figure.
- The share of labelled ways of failing that the review recorded is reported for
  each classification separately.
- How well the predicted catching tests agree with the labelled ones is reported
  as its own figure, computed independently of the share above.
- A figure with nothing to compute from is reported as absent, and never as zero.
- The existing measure of whether two criteria stating the same demand receive
  the same tests is also computed over the tests reached by way of the recorded
  ways of failing.
- Scoring runs from recorded material and issues no live call to a model.
- Every reference set shipped with the harness loads and validates.

## Scope exclusions
- Producing the ways of failing that are scored, and predicting which tests
  would catch one.
- Any rating, conclusion, recommendation or report the review itself produces.
- Which criteria the review derives from a mandate, and how it derives them.
- Judging whether a labelled way of failing is itself the right one to expect.
- Running any code under review.

## Completion expectations
- Implementation.
- A test fails when a reference set naming a criterion its case does not define
  is loaded rather than rejected.
- A test fails when a criterion with no plausible way of failing is stored so
  that it cannot be told apart from one the reference set is silent about.
- A test asserts that a recorded way of failing worded differently from its
  labelled counterpart still matches it.
- A test fails when a disagreement between two classifications is counted as a
  way of failing the review never recorded.
- A test asserts that the share of labelled ways of failing recorded, and the
  agreement between predicted and labelled catching tests, are computed
  independently of each other.
- On a small set whose figures are known by hand, every computed figure equals
  the hand-computed one.
- A test fails when scoring issues a live call to a model.
