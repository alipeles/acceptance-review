# Task
Requirement decomposition must preserve two distinctions when it reads a task
file: an acceptance criterion demanding a test, against the behaviour that test
is about; and a scope exclusion, against work the change must do.

## Constraints
- An acceptance criterion that demands a test yields an obligation whose demand
  is the test, not the behaviour the test is about.
- An obligation demanding a behaviour and an obligation demanding a test of that
  behaviour are never recognised as stating the same requirement.
- A sentence of a given shape yields the same kind of obligation regardless of
  which task file it appears in.
- Sibling bullets under one scope exclusions heading receive the same
  disposition as each other.
- A requirement disposed of without an obligation carries a reason that does not
  itself state a property the change must preserve.
- No obligation is produced whose only satisfying evidence would be a test that
  an excluded thing did not happen.
- Two runs over byte-identical task text produce byte-identical review state.
- Tests issue no live model calls.

## Scope exclusions
- Whether an obligation needs test evidence at all, which is #148.
- Assigning obligation types, which is #205.
- Which open questions are raised, and what they cite, which is #206.
- How finely a single requirement is split into obligations, which is #117.
- Whether obligation identifiers are stable across task-file edits, which is
  #231.
- Measuring how accurate decomposition is, which is #211.

## Completion expectations
- Implementation
- A test asserts that an acceptance criterion demanding a test derives an
  obligation whose demand is the test.
- A test asserts that an obligation demanding a behaviour and an obligation
  demanding a test of that behaviour are not recognised as stating the same
  requirement.
- A test asserts that sibling bullets worded alike under one scope exclusions
  heading receive the same disposition as each other.
- A test asserts that a requirement disposed of without an obligation has a
  reason stating no property the change must preserve.
- A test asserts that two runs over byte-identical task text produce
  byte-identical review state.
