# Task
A repeated review changes a criterion's test-evidence rating only when something
that criterion depends on has changed, and says what that change was.

## Constraints
- A review that has no stored earlier review judges every criterion without
  reference to an earlier rating.
- A repeated review matches each criterion to the stored review's criterion for
  the same requirement, by something that does not move between runs.
- A criterion depends on its requirement text, the set of tests mapped to it, and
  the content of those tests.
- When a repeated review finds a criterion's dependencies unchanged, it carries
  that criterion's stored test-evidence rating forward and makes no model call
  for it.
- When a repeated review finds a criterion's dependencies changed, it judges that
  criterion again, and the judgement is given the stored rating and the changes.
- A repeated judgement that alters a criterion's rating gives a reason, and names
  the change to that criterion's dependencies the reason rests on.
- The change a repeated judgement names is one of the changes it was given.
- The stored earlier review is an input to a repeated review, and two repeated
  reviews from the same stored review and the same inputs produce byte-identical
  review state.
- Tests issue no live model calls.

## Scope exclusions
- Which tests are discovered, and which criteria they are mapped to, which is
  #182.
- Whether a mapping change must likewise be explained, which is #182.
- How many plausible defects a criterion's judgement names, and whether a rating
  requires every one of them to be caught, which is #183.
- Whether a rating that could not be reproduced is reported as unreproducible.
- Whether a carried-forward rating is shown differently from a freshly judged one.
- Whether the controls that make a run reproducible are consolidated into a
  single component, which is #184.
- Assigning obligation types, which is #205.

## Completion expectations
- Implementation
- A test asserts that a review with no stored earlier review judges every
  criterion without reference to an earlier rating.
- A test asserts that a criterion whose dependencies are unchanged keeps its
  stored rating and costs no model call.
- A test asserts that a criterion whose mapped test set has changed is judged
  again.
- A test asserts that a criterion is judged again when the content of a mapped
  test has changed, though the mapped set has not.
- A test asserts that a repeated judgement is given the stored rating and the
  changes to that criterion's dependencies.
- A test asserts that a repeated judgement altering a rating names a change it
  was given, and that a named change it was not given is rejected.
- A test asserts that two repeated reviews from the same stored review and the
  same inputs produce byte-identical review state.
