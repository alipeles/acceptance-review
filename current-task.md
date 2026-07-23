# Task
Add user-configurable ignore patterns for reviewed paths, so an excluded path is invisible to every downstream capability, not just special-cased per capability.

## Constraints
- Gitignore-syntax patterns, read from a `.acceptance/ignore` file in the reviewed repo.
- Applied once at change-set extraction (the lowest layer), so decomposition, coverage classification, unrequested-change detection, and disposition all see the same already-filtered change set.
- A file matching a configured ignore pattern does not appear in the extracted ChangeSet's files at all.
- Ignoring a path must be visible/auditable in CLI output — no silent caps.
- Must work in both committed-revision mode and working-tree mode (including untracked files).
- Existing callers with no `.acceptance/ignore` file must behave exactly as before (full backward compatibility).

## Completion expectations
- Implementation
- Unit tests: ignore file present vs. absent, working-tree/untracked files respect it, CLI renders the ignored-paths section
