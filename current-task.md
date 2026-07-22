# Task
Flag diff regions that no obligation calls for as candidate unrequested changes, giving extra weight to public-interface, dependency, and adjacent-behavior changes.

## Constraints
- Report changes not required by any obligation as candidate unrequested changes, each linked to the specific diff regions.
- Categorize each by nature (public-interface / dependency / adjacent-behavior / internal / other) so the notable ones stand out.
- Produce the detection through a schema-constrained model call recorded for replay; capability tests run off the recorded transcript with no live calls.

## Completion expectations
- Implementation
- Unit tests
