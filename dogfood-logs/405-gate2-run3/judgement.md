# #405 Gate 2, run 3 — judgement

Run `a177c6062ee33dc7`. Verdict INCOMPLETE. **Not clean.** $0.19 this run.

Run-2 finding `test-command-parallel-copies-limit` is now strongly supported.
Four partially supported:

1. `pytest-collected-tests-match-requested-tests` — collect-partial-on-failure
   again. Tool defect, queued (#283 comment).
2. `add-only-test-selection-plugin-and-cache-options` — "must include
   `--no-header`" again. Tool defect, queued (#283 comment).
3. `run-tests-with-exact-command` — the uncaught defect is
   `extra-flags-added-to-user-command`. Both mapped tests,
   `test_the_command_gets_only_the_plugin_the_cache_switch_and_the_tests` and
   `test_listing_tests_adds_only_collect_only_to_that`, assert the whole
   command string by equality, so any added flag fails them. The run itself
   reports `[killed, NOT COUNTED] run-tests-with-exact-command/extra-flags-added-to-user-command`.
   The static judge still said no test catches it. Tool defect (evidence
   judgement, #183): queued as a filing.
4. `print-test-command-each-run` — the no-command case asserted only "locked
   down", not the command. Fair. **Addressed:**
   `test_check_with_no_command_runs_locked_down_and_says_so` now asserts the
   printed interpreter command and the variable-names line.
