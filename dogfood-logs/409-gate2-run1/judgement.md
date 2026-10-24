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

1. **The test-delivery obligation is judged on the wrong kind of evidence —
   tool defect, filed as #410 (under #185).** `network-block-regression-test`
   (`test_demand`) got code evidence "not required — the test itself is the
   deliverable and no separate source change is required" and test evidence
   "indeterminate". The agreed rule is the reverse: an obligation to deliver a
   test is satisfied by code evidence (the test is there and correct), not by
   test evidence. Defect enumeration excludes `test_demand` by design (DR-313
   decision 2), so test evidence can never arrive. This is the one obligation
   the verdict calls unclassifiable, and the cause of UNABLE-TO-DETERMINE.

   *Correction:* the first version of this judgement blamed defect enumeration
   for treating a test-only diff as empty. The owner pointed out the
   code-evidence rule for test-delivery obligations, and that framing was
   withdrawn.

1a. **The two behaviour obligations** (`restore-socket-monkeypatches-after-test`,
   `skip-network-block-for-these-tests`) got code evidence `addressed` (correct)
   and test evidence "no plausible defect … not obtainable here", because
   enumeration does not look at test files. Short of "strongly supported", so the
   gate is not clean on them either. Whether this is a defect or a reasonable
   limit is open with the owner; deliberately not filed.

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
the regression test exists and discriminates (fails both cases at ee52c25,
passes at f66dc6a).
