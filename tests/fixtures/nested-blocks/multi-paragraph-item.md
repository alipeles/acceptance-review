# Task
Rewrite the retry policy.

## Constraints
- Retries are bounded.

  The bound is five attempts, and it is configurable.

  Exceeding it raises rather than returning a partial result.
- Backoff is exponential.

## Scope exclusions
- The streaming client.

  Its retry policy is owned by #300 and is not touched here.

## Completion expectations
- Implementation
- Tests

  Including one that asserts the sixth attempt raises.
