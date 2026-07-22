# Task
Classify each obligation against the diff — Addressed / Partially addressed / Not addressed / Unclear / Requires-non-code-evidence — linking each to the specific diff regions that address it, or explicitly recording that none do.

## Constraints
- This is implementation-coverage only: whether the code changed to address the obligation. It does not prove the obligation works; passing-test evidence is a separate axis (M4/M5) and must not be conflated here.
- Every classification links to exact diff regions (file + hunk) or explicitly records "no corresponding change."
- Produce classifications through a schema-constrained model call recorded for replay; capability tests run off the recorded transcript with no live calls.

## Completion expectations
- Implementation
- Unit tests
