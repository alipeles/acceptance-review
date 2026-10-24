# 414 Gate 1 run 5 — judgement

Run `b1b2749ff056bea4`, continuing run 4 (`0cb3e70c33b8e587`). Claude
Sonnet 5.5. 7 requirements carried, 2 revised (task-02, task-03).
12 obligations, 0 open questions.

## Result: accurate
- task-02 now yields one obligation, `pair-mapping-cache-hit-on-shared-opening`.
  The invariant from my background clause and the widened "every stage"
  obligation are gone.
- task-03 now yields one obligation, `region-source-in-shared-opening`. The
  "one call per defect" obligation from my background clause is gone, and so
  is run 4's duplicate pair. So the duplicate came from my two-sentence
  wording, and it is not a decomposition defect. Nothing to file.
- task-01, task-04, task-05 and exclusion-01..04 were carried unchanged and
  are still accurate.

No invented obligations, and none missing against #414's Deliverable and
Acceptance. Confirmed by the owner 2026-10-24. This breakdown supersedes run
3's; Gate 2 continues from `b1b2749ff056bea4`.
