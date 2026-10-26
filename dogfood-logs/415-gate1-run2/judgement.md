# #415 Gate 1, run 2 — `ab7a337d40ebd7b4`, at 1df6712, continuing run 1

6 requirements, 10 obligations, no open questions. task-01 revised; the other
requirements carried.

## Findings

- task-01 yields `benchmark-cli-runs-report-spend-on-finish` and
  `cli-runs-print-per-stage-usage-table`. The second implies the first: printing
  the table is how the run reports what it spent. **Mostly my wording**: the
  paragraph said it twice ("report what they spent … They print the same
  per-stage usage table"). Linking also left them apart, which is the shape of
  #273 (an explicit obligation restating another is not reconciled with it).
- `check-decompose-keep-reporting-spend` from run 1 is gone, because "as
  `acceptance check` and `acceptance decompose` already do" now reads as
  background. Acceptable: that behaviour is not what this task changes.

## Disposition

Merged task-01's two sentences into one. Re-run as run 3 with
`--continue ab7a337d40ebd7b4`.
