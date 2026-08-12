# Task
The repository's Python sources are formatter-clean and lint-clean, and the
automated build fails any change that leaves them otherwise.

## Constraints
- Every Python file in the repository is formatted the way `ruff format` formats
  it.
- No Python file in the repository violates a selected `ruff check` rule.
- The reformatting alters no program logic.
- The test in `tests/test_partition.py` that expects `Exception` expects instead
  the specific exception type the code under test raises.
- That test is not made to pass by suppressing the lint rule that flagged it.
- The project's development dependencies pin an exact `ruff` version.
- The automated build runs a formatting check over the repository.
- The automated build fails when the formatting check reports a file.
- The automated build fails when the lint check reports an error.
- The automated build's lint step does not discard the lint tool's exit code.
- The automated build checks out the repository's full commit history.
- The automated build's checkout action is at a major version that does not
  target Node 20.
- The automated build's Python setup action is at a major version that does not
  target Node 20.

## Scope exclusions
- Which lint rules are selected.
- Formatting files that are not Python.
- The behaviour of the review pipeline.
- Which Python version the build targets.
- Failures in the test suite that are unrelated to formatting or linting.

## Completion expectations
- Implementation
- A test asserts that every Python file in the repository is formatter-clean.
- A test asserts that no Python file in the repository violates a selected lint
  rule.
- A test asserts that the build's lint step does not discard the lint tool's
  exit code.
- A test asserts that the build runs a formatting check over the repository.
- A test asserts that the build checks out the repository's full commit history.
- A test asserts that the development dependencies pin an exact `ruff` version.
