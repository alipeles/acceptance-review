# Declaration — #327

## Implemented

In `src/acceptance/pipeline.py::run_review`, the split of obligations into
`needs_tests` and `no_tests` moved up, above the defect enumeration call, and
`enumerate_defects` is now given `needs_tests` instead of every obligation. The
split's explanatory comment moved with it and gained a paragraph saying why
enumeration sits below it. Enumeration still runs before `discover_tests`; the
split reads only `required_evidence`, which the decomposition sets.

## Tested

`tests/defects/test_enumeration.py::test_a_criterion_owed_no_test_is_never_offered_to_the_enumerator`
runs a real `run_review` over a two-criterion decomposition: one criterion owed
tests, one scope exclusion marked `code_only` with a reason. It captures every
request the client receives and asserts that the `code_only` criterion's text
appears in no `_Enumeration` request, that the tested criterion's text appears in
one (the control), and that defect sets exist only for the tested criterion. I
saw it fail before the fix on the absence assertion and pass after.

## Left out

- The issue's third Acceptance item, noting the re-recording cost "where the
  figures render". I did not find a code location this belongs in, and the
  likely one (`report.py`) is reserved by another session. So I am noting it
  here: narrowing the enumerator's input orphans the enumeration transcripts
  recorded for any review whose task has a criterion owed no test, and benchmark
  figures spanning the enumeration stage before and after this change are not
  comparable. Prompt text and response schema are untouched, so the per-request
  key of a criterion that is still enumerated does not move.
- The stale comment above the call ("Advisory in this milestone. Nothing below
  reads `defect_sets`") is left as it was; it is out of scope (see `notes.md`,
  Deferred).

## Assumed

- That no consumer of `defect_sets` needs an entry for a criterion owed no test.
  The issue says `derive_support` and `recommend_tests` both filter on the same
  predicate; I relied on that and on the full suite passing, not on reading every
  consumer (`_run_execution_tier`, `judge_pairs`, the ledger sink, the report).

## Unverified

- I did not re-record any transcripts or run a live review to measure the
  saving.
- 24 tests in `tests/benchmark/test_corpus.py` and
  `tests/benchmark/test_rating_regression.py` fail in this session. I verified
  they fail identically on the commit before my change; the error is
  `UnresolvableRevisionError` because this clone is shallow and the corpus pins
  older commits. So those 24 tests say nothing either way about this change.
