# Task
Before any test is looked at, the review records — for each criterion it derived
from the mandate — the concrete ways the delivered code could plausibly fail that
criterion. Each such way is an identified record that persists with the rest of
the review, and that later work refers to by its identifier rather than by
restating it.

## Constraints
- Each recorded way of failing carries an identifier unique within the review,
  the criterion it belongs to, a classification, a free-text description, and the
  regions of changed source it implicates.
- A classification is either a value from a fixed vocabulary or a single escape
  value meaning the vocabulary has no value for this way of failing.
- The recorded ways of failing persist with the rest of the review's state, and a
  review reloaded from storage carries them unchanged.
- The step that produces them is given the criterion and the changed source, and
  is given no test.
- That step is guided by a checklist of ways to fail chosen by the criterion's
  type, and may still record a way of failing that no entry on that checklist
  names.
- Recording no way of failing for a criterion is a valid result for that
  criterion, and carries the reason the set is empty.
- A criterion's set of records is reused rather than produced again exactly while
  both that criterion's text and the contents of the source regions its records
  implicate are unchanged.
- A criterion whose text changed has its entire set produced again, and keeps no
  part of the set recorded for it before.
- A run continuing an earlier run reuses every set it is entitled to reuse, and
  produces again only the sets it is not.
- Where a set was reused rather than produced again, the review says so.
- The review reports the recorded ways of failing.
- Whether the review reports the work complete, and every rating it gives a
  criterion, are what they would be if no way of failing had been recorded at
  all.

## Scope exclusions
- Judging whether any test would fail if the delivered code contained a recorded
  way of failing.
- Deriving any rating, classification or conclusion about a criterion from its
  recorded ways of failing.
- Which criteria the review derives from the mandate, and how it derives them.
- How the review gathers, judges or rates test evidence today.
- Running the delivered code, and altering it to produce a failure.
- Comparing a recorded set against an expected set supplied from outside the
  review.

## Completion expectations
- Implementation.
- A test fails when the step that records ways of failing is given a test.
- A test fails when a criterion with no plausible way of failing is given an
  invented one instead of an empty set carrying its reason.
- A test fails when a set is produced again across two continued runs although
  the criterion's text and the contents of its implicated source regions are both
  unchanged.
- A test fails when a criterion whose text changed keeps any part of the set
  recorded for it before.
- A test fails when a criterion whose text is unchanged has its set produced
  again because a different criterion's text changed.
- A test fails when recording ways of failing changes the review's completion
  conclusion or any criterion's rating.
- Two recorded runs over the same input produce byte-identical review state and
  byte-identical report output.
