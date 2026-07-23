# Task
Collect added/modified tests plus relevant existing tests (by touched symbols, imports, naming, and call graph).

## Constraints
- Structural only, no LLM call — Python AST, matching the M2 change/diff extraction and M2.2 context retrieval.
- Every added/modified test in the change set is discovered directly.
- An existing, untouched test is discovered when it calls a changed symbol, references a changed symbol without calling it, imports a changed module, or is named after a changed symbol.
- Every discovered test records why it was discovered (never zero reasons).
- Bound the repo-wide scan with a budget, flagged (not silently dropped) when the cap is hit.

## Completion expectations
- Implementation
- Unit tests: on a fixture where an existing untouched test covers a changed function, that test is discovered.
