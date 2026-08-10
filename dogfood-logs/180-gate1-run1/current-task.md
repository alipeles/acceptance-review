# Task
A criterion's test-evidence rating is determined by that criterion's own inputs,
so an edit elsewhere in the change cannot move it.

## Constraints
- The judgement of whether a criterion's mapped tests discriminate is requested
  separately for each criterion.
- A criterion's discrimination request carries that criterion and its mapped
  tests, and no other criterion's.
- Editing a test that is mapped to one criterion and not to another leaves the
  other criterion's test-evidence rating unchanged.
- Adding or removing a criterion leaves an unrelated criterion's test-evidence
  rating unchanged.
- How many criteria one discrimination request carries is a run control, and
  changing it invalidates the recorded transcripts.
- A criterion for which no usable judgement is obtained is rated indeterminate,
  and never rated as though its tests discriminate.
- Two runs over byte-identical inputs produce byte-identical review state.
- Tests issue no live model calls.

## Scope exclusions
- Which tests are discovered, and which criteria they are mapped to, which is
  #182.
- How many plausible defects a criterion's judgement names, and whether a rating
  requires every one of them to be caught, which is #183.
- Whether the controls that make a run reproducible are consolidated into a
  single component, which is #184.
- Whether a rating that could not be reproduced is reported as unreproducible.
- Which part of the change a criterion's judgement is shown, beyond the whole
  set of changed source.
- Assigning obligation types, which is #205.

## Completion expectations
- Implementation
- A test asserts that each criterion's discrimination judgement is requested
  separately, rather than all criteria in one request.
- A test asserts that editing a test mapped to one criterion leaves another
  criterion's test-evidence rating unchanged.
- A test asserts that adding a criterion leaves an unrelated criterion's
  test-evidence rating unchanged.
- A test asserts that how many criteria one discrimination request carries is
  folded into the recorded request key.
- A test asserts that a criterion for which no usable judgement is obtained is
  rated indeterminate.
- A test asserts that two runs over byte-identical inputs produce byte-identical
  review state.
