# Task
Detect the §9.4 weak-evidence anti-patterns and flag each with its matching pattern name: assert-not-none/result-exists, circular expected value, incomplete error assertion, requirement-not-exercised, critical-behavior-mocked, unvalidated snapshot.

## Constraints
- Structural detection, no model call.
- Reuse what M5.1-M5.3 already compute rather than recomputing: circular expected value from M5.1's expected-value provenance; requirement-not-exercised and critical-behavior-mocked from M5.3's nominal classification, distinguished by whether mocks are involved.
- The remaining three patterns (non-discriminating assertion, incomplete error assertion, unvalidated snapshot) need new structural detection over a test's raw source.
- An incomplete error assertion may be checked either inside the raises block or in the statements immediately following it — both are valid pytest style.

## Completion expectations
- Implementation
- Unit tests: each §9.4 code example is correctly flagged with the matching pattern name; a genuinely strong test is not flagged.
