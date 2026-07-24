# Task
Fix decomposition so an embedded definitional sub-clause that is a distinct computation is isolated as its own criterion, without over-splitting a single cohesive behavior into facets.

## Constraints
- Sharpen the decompose system prompt so a sub-clause that defines a distinct computation or derived value (a formula with its own logic, introduced by "where", "using", "based on") is isolated as its own obligation.
- Keep a single cohesive behavior — a parse, a lookup/mapping, a formatting or display rule — as one obligation even when it spans several inputs or fields.
- The behavior change is prompt-only; injected-response capability tests are unaffected.

## Completion expectations
- The sharpened prompt
- Live before/after verification, since prompt quality cannot be asserted by injected-response tests: archetype #4 isolates the daily-rate computation; archetypes #1 and #2 do not over-split a cohesive behavior.
