# #335 Gate 1, run 2 — judgement

Run `58eb650f5d04d24e`, continuing run 1 (`384604f689ad8fca`). Two changes to the
task file: the background paragraph removed, and the second question restated as
what the software does rather than as a question.

## Fixed by the rewording

The background paragraph is gone, and with it the eight obligations it produced,
including the three demanding the old one-call design and its failure rates. The
duplicate pair from run 1's `task-02` went with it: the sentence now lives in
`task-01` as one obligation, `two-questions-sequence`.

## Not fixed

- **`task-03` → `changed-behaviour-matches-defect-behaviour`** still asserts that
  every changed edit matches its defect, and the new sentence *"An edit whose
  changed behaviour does not match is refused"* yields no obligation. Rewording
  changed nothing, so this is a tool defect, not wording. Queued in
  `docs/DEFERRED.md` as a drafted filing under #181, the decomposition umbrella.
- **`constraint-01-open-1`** is the same wrong question as run 1. It was
  *carried* by `--continue`, not re-derived, so run 2 is not independent
  evidence that it reproduces. Still a stop under the Gate 1 table.

## Correct

`task-02`'s four obligations, `task-04`, `task-05`, the exclusions and the
documentation line.

## Missing

The constraint's obligation (neither question sees the tests or their results),
because the open question stands in its place.
