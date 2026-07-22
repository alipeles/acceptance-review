# Task
Analyze uncommitted working-tree changes against a base revision, so the checker works before a PR or commit exists (§5.1).

## Constraints
- A dirty working tree (staged and/or unstaged changes, no head commit required) must produce the same ChangeSet shape M2.1 produces for a committed diff.
- Untracked new files must be detected as added files, not silently ignored.
- Do not require a head commit to exist.

## Completion expectations
- Implementation
- Unit tests
