# Task
Parse the nine-section §7.4 builder declaration when present; when absent, record a minor finding and proceed with a full review (§7.4 optional-by-default).

## Constraints
- Stage 1 is entirely local mode (`Review.mode == "local"`) — the checker has no GitHub App, hosted service, or CI access, and no other mode exists yet (Mode B / GitHub Acceptance Review is Stage 2, out of scope). "Optional by default in local mode" therefore names Stage 1's only mode, not a branching condition; this task adds no mode-determination logic.
- The declaration's absence must never block or degrade the rest of the review.
- A declaration may be partial (some of the nine sections omitted); a partial declaration is still a valid declaration, not an error.
- A declaration is a claim, not proof — parsing must not compare its content against evidence or judge truthfulness; that is a separate, later capability.

## Completion expectations
- Implementation
- A run without a declaration completes and emits the "declaration absent" minor finding.
- A run with one populates the declaration state, including a partial (not all nine sections present) declaration.
