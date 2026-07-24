# Task
Classify each criterion's test-evidence strength into the §9.3 classes — strongly / partially / nominally / unsupported / indeterminate — at the static tier, with a linked, self-justifying explanation.

## Constraints
- Consume M5.2's per-criterion discrimination verdicts; this is a deterministic reduce, not a fresh model judgment.
- Map on the single bright line: all named plausible defects caught is strongly supported; at least one but not all is partially supported; a mapped test that catches none is nominally supported; no mapped test at all is unsupported; a mapped test with no defect judged is indeterminate.
- Do not invent requires_other_evidence from discrimination alone — there is no such signal in the verdicts.
- Each classification links to the exact mapped tests, and a nominal test that bypasses the behavior via a mock cites the mock (from M5.1's extracted mocks).

## Completion expectations
- Implementation
- Unit tests: archetype #3's superficial test yields nominal for the rules it never checks; archetype #6's mocked-out core behavior is nominal with the mock cited; each classification links to the exact mapped tests.
