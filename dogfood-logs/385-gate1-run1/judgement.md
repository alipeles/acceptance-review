# 385 Gate 1 run 1 — judgement

**Result:** aborted; no decomposition produced.

The summary step (`requirement/summary.py::decide_spans`) rejected the model's
split of the Task paragraph's second paragraph. Claude Sonnet 5.5 split "Jev's
probability that the test fails decides the pair on its own at 0.34 or more (the
test fails) and at 0.24 or less (the test survives)" into two claims and
repeated the shared subject in the second, so span 4 is not a substring and the
run stops with a SchemaValidationError.

**Triage:** tool defect, not a task-file problem. The split is a reasonable
reading; the exact-substring rule and the stop-the-run handling are the
defect. Queued as a filing under #181 (decomposition umbrella) in
docs/DEFERRED.md, "A sentence split into two claims with a shared subject
aborts decomposition".
