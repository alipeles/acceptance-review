# Task

A project whose tests live in a subdirectory with their own `pyproject.toml` and
virtualenv has its tests run by `acceptance check`, using the project's own
dependencies, and the tests pytest collects are recognised as the tests the tool
asked for.

To make that possible, the user tells the tool once, per repository, the command they already
use to run their tests — for example `cd api && .venv/bin/python -m pytest` —
and the tool runs the project's tests with exactly that command, adding only
which tests to run, its own pytest plugin, and the options it needs to list
tests and to leave no pytest cache in the project. When
no test command is set and the tests cannot be run, the tool says that a test
command needs to be set, rather than reporting that pytest declines the tests.

Tests run this way run as they do on the user's own machine: with the user's
environment variables and with network access, so a suite that needs a local
database and a variable such as `DATABASE_URL` can run.

Because the tool runs the tests many times, including against deliberately
broken copies of the code, setting the test command shows the user that risk in
plain words and saves the command only after the user explicitly agrees. If the
saved command changes, the user is asked to agree again. Each run prints the
test command it uses and the names of the environment variables passed to the
tests; it never prints their values.

By default the tool never runs two copies of the project's tests at the same
time. When setting the test command, the user may say how many copies can
safely run at once; the tool then runs up to that many, and tells each copy
which one it is through an environment variable, so that a project can give
each copy its own database.

Test discovery no longer offers a pytest fixture, such as a `conftest.py`
function named `test_db_url`, as a test.

The spec's execution-safety wording is updated to match.

## Scope exclusions
- Working out a test command, an interpreter or a directory from the project's
  files.
- Judging whether a database or service the tests use is safe to use.
