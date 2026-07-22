# Task
Feed M3.1's implementation-coverage classifications and M3.2's unrequested-change detections into the M-B0.3 gap-detection (recall) and false-alarm (precision) scoring.

## Constraints
- Reuse the existing §11.1 gap metric (`scoring.py`); do not redefine it.
- A non-addressed coverage classification becomes a Finding linked to the obligation it concerns, so it is matchable against ground-truth gaps.
- Keep the hook lighter than the full checker pipeline (M-B0.2's run_case) — no test execution, same shape as M1.4's decompose_case.

## Completion expectations
- Implementation
- Unit tests: archetypes #1, #2, and #8 each contribute a real, hand-calculable gap_recall/gap_precision figure.
