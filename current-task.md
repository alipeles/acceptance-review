# Task
Extract the Git change set between a base and head revision: changed files, a source-vs-test partition, hunk-level diffs, and config/dependency-file changes.

## Constraints
- Categorize every changed file as source, test, config, or other.
- Represent diffs at hunk granularity, not as one flattened string per side.
- Correctly detect added, modified, deleted, and renamed files.

## Completion expectations
- Implementation
- Unit tests
