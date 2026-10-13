# 338 Gate 2 run 2 — judgement

Run continuing 96b59ff781e87bca. Base 10cdf2d, head d8b7b0e. Verdict INCOMPLETE.
Not clean.

## Run 1's real finding is closed
Obligations 7 and 19 moved from partially to strongly supported ("Changes
since c204c348" in output.log), on the two new
`TestTheCliReportsCostPerDefect` tests.

## Remaining findings — all attributed to tool defects, drafts in docs/DEFERRED.md
- Obligation 23, partially addressed: same as run 1 (#272, plus a misreading of
  the usage-only label as a request change).
- Obligations 12 and 13, "test evidence: not required": same as run 1 (a new
  sub-issue of #183, linked to #196).
- Unrequested change 1, [risky], the `label` keyword: same as run 1, reworded
  (a new sub-issue of #185).
- NEW: unrequested change 11, [separable], the sibling guard test file. The same
  report cites a test from that file as evidence 11.5 for obligation 11. Run 1
  did not report it. Drafted: a new sub-issue of #185.

## Observed, not filed
Nine candidate tests were set aside because the unmodified control run
exceeded its 300s budget; run 1 set aside none for that reason. No rating rests
on them, and I believe the cause was load from concurrent sessions on this
machine rather than anything in this change. If it recurs on a quiet machine,
it is a filing.
