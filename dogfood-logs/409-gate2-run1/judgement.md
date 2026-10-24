# 409 Gate 2, run 1 — judgement

Run `fe4faf6c875c884f`, `check --base 81a1d41 --head f66dc6a --continue
851b6085fab262e7 --mode record`. Verdict **UNABLE-TO-DETERMINE**. **Not clean.**

The whole delivery is in `tests/test_execution_sandbox.py`: two
`monkeypatch.setenv(netblock.ALLOW_NETWORK_VAR, "1")` lines and a new
parametrized test,
`test_a_test_that_configures_the_plugin_in_process_leaves_socket_untouched`.
That test failed on both cases before the fix (commit ee52c25) and passes after
(f66dc6a); full suite 1926 passed.

## Findings

1. **No test mapped to any obligation; obligation 3 indeterminate — tool
   defect.** Defect enumeration for all three task obligations says "No
   production code was changed … the diff is empty". The diff is not empty; it
   is entirely in a test file, and enumeration only looks at non-test code. With
   nothing enumerated, no mapping or execution stage ran (none appears in the
   model-usage table), so the regression test that directly checks obligations
   `restore-socket-monkeypatches-after-test` and `network-block-regression-test`
   is never considered. Any task whose deliverable is a change to tests can
   therefore never reach "strongly supported". Not covered by #402 (enumeration
   misses a defect in changed production code) or #327 (defects enumerated for
   criteria owed no test). Drafted as a new filing under #183.

2. **The requested regression test is reported as an unrequested change
   (`in_service`) — tool defect, same family as #376.** The note says the test
   "adds a new test path beyond simply verifying the socket monkeypatches are
   restored". The task file asks for exactly that test (`task-02`). #376 covers
   a test file cited as evidence being reported `separable`; here the test is the
   deliverable of a `test_demand` obligation, and was reported `in_service`.
   Comment on #376 drafted.

3. Obligation 4, `no-network-block-implementation-change` — addressed, correct:
   `src/acceptance/execution/netblock.py` is untouched.

No code change can address 1 or 2: the code is the fix the issue asked for, and
the evidence the tool needs (the regression test) exists and discriminates.
