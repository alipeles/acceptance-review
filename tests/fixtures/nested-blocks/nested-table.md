# Task
Classify each evidence tier.

## Constraints
- Every tier maps to exactly one authorised producer.

  | tier | producer |
  |---|---|
  | builder-claim | the declaration |
  | static | the analyser |
  | defect-killed | mutation runs |
- A component never emits a tier above the one it is authorised to produce.

## Completion expectations
- Implementation
