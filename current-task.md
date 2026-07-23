# Task
Auto-exclude the CLI's --task file from the reviewed diff, and make extra ignore patterns additive to the repo's own .acceptance/ignore rather than replacing it.

## Constraints
- The task file must never appear as a coverage claim or an unrequested-change flag in `classify` output, regardless of its name or location within the repo.
- A task file outside the reviewed repo must be handled gracefully (nothing to exclude).
- Ignore patterns from the repo's own `.acceptance/ignore` file and any caller-supplied extra patterns must both apply together — adding an extra pattern must not silently disable the repo's own ignore configuration.

## Completion expectations
- Implementation
- Unit tests: a task file inside the repo is excluded from the diff; a task file outside the repo is unaffected; extra patterns and the ignore file combine rather than override.
