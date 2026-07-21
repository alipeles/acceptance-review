# Task
Parse the local task file (`current-task.md`, §7.1 format) into structured task content the checker can reason over.

## Constraints
- Extract the task behavior, constraints, scope exclusions, and completion expectations as separate fields.
- Preserve a source-text reference (the exact span) for every extracted item.
- Accept the §7.1 structure: `# Task`, `## Constraints`, `## Completion expectations`, and an optional scope-exclusions section.

## Completion expectations
- Implementation
- Unit tests
