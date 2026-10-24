# 310 Gate 1 run 1 — judgement

Run `39e676bdc29bee30`, main afbf9b9, model `anthropic/claude-sonnet-5-5`.
5 requirements, 9 obligations, 0 open questions. Cost $0.27.

## Obligations
- `task-01` -> `scope-exclusion-bullets-become-absence-obligations` and
  `scope-exclusion-with-rationale-clause-stays-absence`. Real and correct: the
  general rule and the trailing-clause case are separate Acceptance items on #310.
- `task-02` -> four obligations. `scope-exclusion-obligation-judged-on-code-evidence-alone`
  and `scope-exclusion-review-requests-no-test` say the same thing. **Task-file
  wording defect, not a tool defect:** the paragraph stated the rule twice ("judged
  on code evidence alone" and "never asks for a test of it"). Rewritten for run 2.
  `scope-exclusion-review-checks-diff-for-excluded-work` describes what the coverage
  stage already does for an obligation satisfied by absence; also dropped by the
  rewrite, since it restates the same rule a third way.
  `scope-exclusion-consistent-coverage-status` is real (#310 Acceptance item 4).
- `task-03` -> `regression-case-scope-exclusion-explanatory-clause`, `tests_only`.
  Correct: the regression case is itself a deliverable.
- `exclusion-01`, `exclusion-02`: both in the absence form, `code_only`, satisfied by
  absence. Correct.

## Open questions
None.

## Tool defects
None attributed.
