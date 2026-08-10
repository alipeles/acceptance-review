# Judgement — #234 Gate 1, run 2

Re-run after removing the bare `Implementation` bullet from Completion
expectations (run 1's finding). 13 requirements, 10 obligations, 3 disposed of.

## Clean

- **No invented obligations.** Every obligation traces to one bullet.
- **None of the real ones missing.** Six Constraints → six obligations; three
  test demands → three `test_demand` obligations; the Task line → one
  functional obligation.
- **Exclusions uniform.** All three disposed of without an obligation, each
  reason naming the excluded thing and asserting no property of the change.
- **No open questions.** Nothing to triage.

Typing looks right: the two "does not depend on X" constraints came back
`invariant` and `compatibility` rather than `functional`, and the three
"A test asserts…" bullets came back `test_demand` — the distinction #232
shipped, holding on a task file it was not tuned against.

## Known, not this task

Obligation identifiers differ from run 1's for the requirements that did not
change (`test-repeat-materialization-stable-commit-identifiers` is the only one
that survived verbatim). That is #231, already filed.

`task-01` restates what `constraint-01`, `constraint-02` and `constraint-06`
also state, so the same behaviour carries four obligations. That is granularity
(#117), excluded from this task.

Gate 1 passed at `4b78d62`.
