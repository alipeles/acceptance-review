# Judgement — #214 Gate 2, run 1

Base `0923f77`, head `be4367d`. Superseded by run 2; the combined judgement,
including the run-1 vs run-2 rating comparison, is in
`dogfood-logs/214-gate2-run2/judgement.md`.

## Result

**INCOMPLETE.** Two coverage gaps, two obligations with weak test evidence.

## All four findings were real

None was attributed to a tool defect. Each was a genuine hole in this change's
own tests:

1. `byte-identical-inputs-byte-identical-review-state` — code evidence
   **unclear**. There was no test. The obligation was in my own mandate and I
   did not write it.
2. `completion-10-test-demand-byte-identical-review-state` — same omission on
   the test-demand side.
3. `declined-requirement-coverage-accounting` — partially supported. The test
   used a bare `- Implementation` marker, which any implementation credits,
   including one that re-judges the decline. It could not have failed.
4. `record-coverage-on-result-and-report` — partially supported. The coverage
   field was asserted; that the *report* renders it was not.

All four are fixed in `bb1f1ef`. Findings 3 and 4 moved to **strongly
supported** in run 2, and both coverage gaps closed.
