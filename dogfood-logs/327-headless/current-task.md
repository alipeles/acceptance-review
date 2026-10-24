# Task

The review asks the defect enumerator only about criteria that are owed test
evidence. A criterion whose required evidence demands no test is never offered
to the enumerator, so it costs no enumeration call and produces no defect set.
A criterion that does require tests is enumerated for exactly as before.

Enumeration still happens before any test is discovered. The set of criteria
it is given is decided from the decomposition alone, so it cannot be influenced
by which tests exist.

A regression test asserts, against the enumeration requests the review
actually sends, that a criterion owed no test appears in none of them, and that
a criterion owed tests does appear.

## Scope exclusions

- The prompt text and response schema of the enumeration stage are unchanged.
- The stages that consume defect sets are unchanged.
