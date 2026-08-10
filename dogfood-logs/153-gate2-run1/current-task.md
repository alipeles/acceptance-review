# Task
A requirement stating a boundary the change must not cross is confirmed by
examining the change for a breach, and never by demanding a test of it.

## Constraints
- A bullet under a scope exclusions heading yields an obligation.
- An obligation derived from a scope exclusion admits code evidence only.
- No test is recommended for an obligation that admits code evidence only.
- An obligation that admits code evidence only is never rated on test evidence,
  and its want of test evidence never makes the completion verdict incomplete.
- A change that crosses a stated boundary is reported as a breach, citing the
  place in the change where it crosses.
- A boundary the change respects is confirmed by a single claim over the whole
  set of changes examined, not by listing the individual changes in that set.
- A confirmation that a boundary was respected names the set of changes that was
  examined to reach it.
- A confirmation that a boundary was respected is not stated more strongly than
  the examination that produced it supports.
- A reader of the report can tell an obligation that admits code evidence only
  from an obligation whose test evidence is missing.
- Two runs over byte-identical task text produce byte-identical review state.
- Tests issue no live model calls.

## Scope exclusions
- Which obligations other than those derived from scope exclusions admit code
  evidence only, which is #148.
- Assigning obligation types, which is #205.
- Which open questions are raised, and what they cite, which is #206.
- How finely a single requirement is split into obligations, which is #117.
- Whether obligation identifiers are stable across task-file edits, which is
  #231.
- Measuring how accurate decomposition is, which is #211.
- Which tests are discovered, and which obligations they are mapped to.

## Completion expectations
- Implementation
- A test asserts that a bullet under a scope exclusions heading yields an
  obligation admitting code evidence only.
- A test asserts that no test is recommended for an obligation admitting code
  evidence only.
- A test asserts that an obligation admitting code evidence only does not make
  the completion verdict incomplete for want of test evidence.
- A test asserts that a change crossing a stated boundary is reported as a
  breach citing where it crosses.
- A test asserts that a respected boundary is confirmed by one claim naming the
  set of changes examined, rather than by listing each change in it.
- A test asserts that two runs over byte-identical task text produce
  byte-identical review state.
