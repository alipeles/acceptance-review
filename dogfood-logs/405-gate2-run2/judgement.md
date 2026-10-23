# #405 Gate 2, run 2 — judgement

Run `0cf1a8e59e50a913`. Verdict INCOMPLETE. **Not clean.** Task file reworded
(owner-approved) so task-02 says the tool adds "which tests to run, its own
pytest plugin, and the options it needs to list tests and to leave no pytest
cache in the project".

Run-1 findings resolved: no set-aside test, no human-review claim, no
`separable` change; `test-command-provided-once-per-repo` and
`reconfirm-on-command-change` now strongly supported.

Remaining partially supported, four:

1. `pytest-collected-tests-match-requested-tests` — the same
   collect-partial-on-failure "defect" as run 1. Tool defect, queued (#283
   comment).
2. `run-tests-with-exact-command` — uncaught defect: extra options could be
   added. The run path was pinned verbatim; the listing path was not.
   **Addressed:** `test_listing_tests_adds_only_collect_only_to_that`.
3. `add-only-test-selection-plugin-and-cache-options` — the recommendation
   says "a correct implementation must include `--no-header`". That is
   inverted: the change removed `--no-header` precisely so only the allowed
   additions remain. Tool defect: an enumerated defect derived from the diff's
   removed line, contradicting the obligation. Added to the #283 draft.
4. `test-command-parallel-copies-limit` — the printed form should read as a
   maximum. **Addressed:** the check-wiring test now asserts
   "(up to 2 at once)".

Also seen: a LiteLLM "Give Feedback / Get Help" banner at the top of stderr
with no error text; the run completed. I believe a provider error was retried.
Not a finding about #405.
