# Task
Wire the decomposition output (M1.2/M1.3) into the benchmark's decomposition-accuracy metric (M-B0.3), so archetype cases report a real decomposition-accuracy number.

## Constraints
- Decomposing a case only needs its task text, not a materialized repo — the hook should not require the full check pipeline's git/diff machinery.
- Stay replay-first: the scoring hook's own tests inject a recorded model response, no live calls.

## Completion expectations
- Implementation
- Unit tests
