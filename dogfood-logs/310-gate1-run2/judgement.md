# 310 Gate 1 run 2 — judgement

Run `b51f520cab69ba16`, continuing `39e676bdc29bee30`, main afbf9b9, model
`anthropic/claude-sonnet-5-5`. 4 requirements carried, 1 revised (`task-02`).
7 obligations, 0 open questions. Cost $0.06.

## Obligations
- `task-01` -> `scope-exclusion-bullets-become-absence-obligations`,
  `scope-exclusion-with-rationale-clause-stays-absence`. Unchanged from run 1; correct.
- `task-02` (reworded to state the code-only rule once) ->
  `scope-exclusion-obligations-require-code-evidence-only` and
  `scope-exclusion-consistent-coverage-status`. The run 1 duplicate is gone. Correct.
- `task-03` -> `regression-case-scope-exclusion-explanatory-clause`, `tests_only`. Correct.
- `exclusion-01` -> `no-change-to-required-evidence-for-other-sections`; `exclusion-02` ->
  `no-change-to-stage-model-selection`. Absence form, `code_only`. Correct.

No invented obligations; none missing against #310's four Acceptance items.

## Open questions
None.

## Reproduction of #310 on Sonnet 5.5 (same session, not committed as runs)
- `dogfood-logs/338-gate1-run3/current-task.md`: all four exclusions in the absence
  form, `code_only`, including the Codex-adapter bullet that inverted on gpt-5.4-mini.
- A task file built around #302's bullet "Model calls issued by the measurement
  harness, which is not part of a review run." with three sibling exclusions:
  all four in the absence form.
- 0 of 2 attempts reproduce it. The defect was intermittent on gpt-5.4-mini, so
  this does not prove it gone; it does mean a prompt-only fix cannot be shown to
  work on this model, which shapes the plan towards a code-side guarantee.

## Tool defects
None attributed.
