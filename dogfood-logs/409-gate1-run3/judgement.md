# 409 Gate 1, run 3 — judgement

Run `851b6085fab262e7`, `decompose --continue f88d860009b99893`,
3 requirements → 4 obligations, 0 open questions.

Only change from run 2: the first test's name. Issue #409 calls it
`test_a_budget_that_cannot_be_enforced_declines_the_run`, which does not exist;
the test at `tests/test_execution_sandbox.py:167` is
`test_the_per_test_budget_is_refused_rather_than_ignored_when_unenforceable`.

## Breakdown — accurate, same as run 2

- `restore-socket-monkeypatches-after-test` `[regression]` — correct.
- `skip-network-block-for-these-tests` `[functional]` — correct.
- `network-block-regression-test` `[test_demand]` — correct.
- `no-network-block-implementation-change` — correct (carried).

The two `task-01` obligation ids changed slightly (`-tests` → `-test`,
`-in-these-` → `-for-these-`) because the requirement was revised; their text
did not change in substance. Not a defect: a revised requirement is re-derived.

No open questions to triage.
