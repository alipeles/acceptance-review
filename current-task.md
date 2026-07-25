# Task
Parse the nine-section §7.4 builder declaration when present; when absent, record a minor finding and proceed with a full review (§7.4 optional-by-default).

## Constraints
- The declaration is optional by default in local mode; its absence must never block or degrade the rest of the review.
- A declaration may be partial (some of the nine sections omitted); a partial declaration is still a valid declaration, not an error.
- A declaration is a claim, not proof — parsing must not compare its content against evidence or judge truthfulness; that is a separate, later capability.

## Completion expectations
- Implementation
- A run without a declaration completes and emits the "declaration absent" minor finding.
- A run with one populates the declaration state, including a partial (not all nine sections present) declaration.
