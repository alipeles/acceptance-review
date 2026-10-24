# Task

The tests `test_the_per_test_budget_is_refused_rather_than_ignored_when_unenforceable` and
`test_the_per_test_budget_still_applies_without_a_report_path` in
`tests/test_execution_sandbox.py` leave the test suite's own process with its
original `socket.create_connection`, `socket.getaddrinfo` and
`socket.socket.connect`, so tests that run after them see an unmodified
`socket` module. Neither test is about the network block, so each runs with the
block skipped rather than installing it and removing it afterwards.

A regression test that fails if either test leaves the network block installed
is part of the deliverable.

## Scope exclusions
- Changing how the network block itself works for the projects the tool runs.
