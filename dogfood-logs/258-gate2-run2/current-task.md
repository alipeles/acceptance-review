# Task
No test's outcome or case list depends on the task file at the repository root,
which is a scratch input rewritten for every task.

## Constraints
- No test reads the task file at the repository root.
- The task-file parse test takes its inputs from the committed task files under
  `dogfood-logs/`.
- The parse test runs one case per committed task file.
- The parse test asserts, for each case, that the parsed behavior, constraints
  and completion expectations are each non-empty.
- The parse test asserts, for each case, that every parsed span reproduces its
  own text from the source it was parsed from.
- The region-coverage case list is built only from the committed task files
  under `dogfood-logs/`.
- The region-coverage case list is non-empty.
- The region-coverage case list omits a path that is not present in the tree.
- A test run reports no failures when no task file is present at the repository
  root.
- The parse test's documentation states which inputs it covers.

## Scope exclusions
- Whether the task file at the repository root is tracked by version control.
- How a task file is parsed into sections.
- How region coverage is computed.
- Which sections a task file is required to contain.
- The content of the committed task files.

## Completion expectations
- Implementation
- A test asserts that parsing succeeds for every committed task file under
  `dogfood-logs/`.
- A test asserts that the region-coverage case list is non-empty.
- A test asserts that no path in the region-coverage case list lies outside
  `dogfood-logs/`.
- A check asserts that no test reads the task file at the repository root.
