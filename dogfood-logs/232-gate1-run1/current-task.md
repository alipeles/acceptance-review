# Task
Requirement decomposition mis-shapes two kinds of task-file text.

An acceptance criterion phrased "a test asserts that X" is derived into an
obligation stating X, with the demand for a test removed. That obligation is
indistinguishable from an obligation to implement X, so a review can report the
behaviour delivered while the demanded test was never written.

A bullet under a scope exclusions heading is dispositioned inconsistently.
Siblings worded alike receive different treatment within a single run and
different treatment between runs, and some are disposed of with a reason that
states a property the change must preserve — an obligation written into a
free-text field instead of yielded.

Make both kinds of text derive predictably.

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
