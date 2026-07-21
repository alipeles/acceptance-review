# Task
For each changed code region, retrieve the enclosing definition and its direct in-repo call sites, within a bounded retrieval budget.

## Constraints
- Find the innermost function/class/method definition that encloses each changed line, via Python AST parsing.
- Retrieve direct call sites of each changed definition elsewhere in the repo.
- Respect a configurable budget cap (files scanned, call sites per definition); mark results truncated when the cap is hit rather than scanning unbounded.

## Completion expectations
- Implementation
- Unit tests
