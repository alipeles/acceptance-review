# #348 Gate 1, run 2 — run `93fa206c07245a75`

Completed: 12 requirements, 25 obligations, no open questions. Run 1's task file
with "exactly as today" deleted from task-03.

## Obligations I would not defend

- **`stop-paying-for-covered-defect-questions`** (task-01) duplicates
  `stop-asking-after-configured-number-of-catching-tests` (task-02), and the two
  disagree: task-01's reads "once one test", task-02's reads "the configured
  number". **Cause: my wording.** The opening paragraph argued from a one-kill
  rule while the next made it configurable. Rewritten for run 3.
- **`defect-test-catch-judgment`** and **`defect-covered-on-first-catching-test`**
  (task-01) are the background the paragraph gives — what the review already
  does — derived as obligations. Both are true of the code today and stay true,
  so they are not wrong, but they are context, not the change. The same pattern
  is already queued ("Context stated as current behaviour becomes an obligation
  to preserve it", `docs/DEFERRED.md`, 2026-08-19). Reducing the background
  in the run-3 rewrite rather than filing again.

## Accurate

task-02 through task-06, all three Constraints and all three Scope exclusions
decompose to what the paragraph says. `unasked-pair-not-answered` and
`unjudged-recorded` are thin but true.

## Open questions

None raised. Expected under #303 (decomposition cannot raise an open question
about a requirement that also yields obligations), not evidence the file is
unambiguous.
