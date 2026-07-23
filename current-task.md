# Task
Map each candidate test to the obligation(s) it purports to evidence, and flag obligations with no mapped test.

## Constraints
- Candidate tests come from M4.1 discovery; obligations from M1.
- Mapping is the precision step over recall-forward discovery: judge which obligation(s), if any, a test's assertions are actually aimed at — not merely that it touches changed code.
- A test may map to zero, one, or several obligations; obligations with no mapped test are flagged unmapped.
- "Purports to evidence" is weaker than "proves" — do not judge test strength here; that is a later step.
- The mapping is a schema-constrained model call recorded for replay; capability tests run off the recorded transcript with no live calls.
- Populate each obligation's test_evidence so the §11.1 mapping-accuracy metric scores a real number against archetype labels.

## Completion expectations
- Implementation
- Unit tests: on the §9.1-style example each derived criterion is either mapped to a test or flagged unmapped, and mapping-accuracy reports a number vs archetype labels.
