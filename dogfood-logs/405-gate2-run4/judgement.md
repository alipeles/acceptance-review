# #405 Gate 2, run 4 — judgement

Run `4907b8a4e90e2e8a`. Verdict INCOMPLETE. **Not clean.** $0.06 this run.
No set-aside test, no human-review item, no `separable` or risky change, no
open question.

Four partially supported, all attributed to the tool, each with a queued draft:

1. `pytest-collected-tests-match-requested-tests` — collect-partial-on-failure,
   the documented design. #283 comment.
2. `add-only-test-selection-plugin-and-cache-options` — "must include
   `--no-header`", the inverse of the obligation. #283 comment.
3. `run-tests-with-exact-command` — `extra-flags-added-to-user-command` judged
   uncaught by two exact-equality tests that the run's own injection shows
   killing it. New sub-issue of #183.
4. `print-test-command-each-run` — `acceptance recommendation --criterion
   print-test-command-each-run` prescribes a test whose four required
   assertions are exactly those of the mapped test
   `test_check_with_no_command_runs_locked_down_and_says_so`. #225 shape (the
   recommendation prescribes a test already in the mapped set). #225 comment.

Nothing further is addressable without changing tests that already do what
the recommendations ask.
