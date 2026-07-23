# Task
For each mapped candidate test, extract its structural facts: what production code it exercises, what it asserts, the fixtures and mocks it uses, its inputs, and — the key one — the provenance of its expected value.

## Constraints
- Structural only, Python AST, no model call — the semantic discrimination judgment (would the test fail under a plausible defect?) is a later step.
- Populate the existing §15 TestEvidence fields: identifier, location, inputs, fixtures, assertions, expected_value_provenance, mocks, mapped_obligations.
- Expected-value provenance must flag circular evidence: when the expected value is computed from the same production code the test claims to verify, so a defect corrupts both sides of the assertion equally.
- The production symbols under test are the names a test imports from a changed source module.
- Take mapped tests from M4.1 discovery + M4.2 mapping.

## Completion expectations
- Implementation
- Unit tests: for archetype #5 the analyzer identifies that the expected value is produced by the same production function (circular provenance); an independent literal expected value is not flagged circular.
