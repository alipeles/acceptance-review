# Task
A criterion's test-evidence rating is re-derived only when that criterion's own
inputs changed. Its inputs are its requirement text, the set of tests mapped to
it, and the contents of those tests.

## Constraints
- A criterion whose requirement text, mapped test set and mapped test contents
  are all unchanged keeps the rating stored for it.
- A criterion whose requirement text, mapped test set and mapped test contents
  are all unchanged is not asked about in the evidence-judgement request.
- A criterion is compared by the contents of the tests mapped to it, not by
  whether a file containing one of those tests was touched.
- A criterion whose mapped test set gained or lost a member is judged again.
- A criterion whose requirement text changed is judged again.
- The earlier rule that decided staleness from whether a cited file was touched
  is removed rather than left in place beside the new one.
- Deciding whether a criterion's implementation coverage is re-derived is
  separate from deciding whether its test-evidence rating is re-derived.
- A review repeated over the same stored state and the same inputs produces the
  same review state as the one before it.

## Scope exclusions
- Making the set of tests mapped to a criterion stable across runs.
- Whether a rating is correct on its merits.
- Which defects the judge names for a criterion it does judge.
- Changing how a re-judgement that names no change is rejected.
- Selecting which stored earlier state a repeated review continues.
- Narrowing which criteria are judged again in any stage other than
  test-evidence judgement.

## Completion expectations
- Implementation
- A criterion with unchanged requirement text, unchanged mapped test set and
  unchanged mapped test contents keeps its stored rating and is not asked about
  in the evidence-judgement request.
- Adding a test to a file that already holds a mapped test leaves unchanged the
  rating of a criterion whose own mapped tests were not edited.
- Editing a test mapped to one criterion leaves every other criterion's rating
  unchanged.
- A criterion whose mapped test set gained or lost a member is judged again.
- A criterion whose requirement text changed is judged again.
- No rule deciding staleness from whether a cited file was touched remains in
  the delivered code.
- Implementation-coverage staleness and test-evidence staleness are decided
  separately.
- Two reviews over the same stored state and the same inputs produce
  byte-identical review state.
- The findings recorded as correct in `tests/fixtures/rating-stability/` are
  still found.
