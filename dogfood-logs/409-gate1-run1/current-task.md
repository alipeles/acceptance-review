# Task

Two tests in `tests/test_execution_sandbox.py`,
`test_a_budget_that_cannot_be_enforced_declines_the_run` and
`test_the_per_test_budget_still_applies_without_a_report_path`, call the
network-blocking pytest plugin's `pytest_configure` directly. That installs the
network block in the test suite's own process and never removes it, so every
test that runs afterwards finds `socket.create_connection`, `socket.getaddrinfo`
and `socket.socket.connect` replaced.

When the work is done, both tests leave the process's `socket` module as they
found them: after either test runs, `socket.create_connection`,
`socket.getaddrinfo` and `socket.socket.connect` are the original functions.
Neither test is about the network block, so each should skip installing it
rather than install and remove it.

This is a reported defect, so a regression test that fails while the block is
left installed and passes once it is not is part of the deliverable.

## Scope exclusions
- Changing how the network block itself works for the projects the tool runs.
