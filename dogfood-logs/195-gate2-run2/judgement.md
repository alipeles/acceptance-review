# #195 Gate 2 run 2 — judgement

INCOMPLETE, and the interesting round. 1 flagged obligation became 19 on a diff
that only added a test — #191's shape, and DR-180 forbids dismissing it as
instability without checking merits first.

Checked. One real gap (`no-live-model-calls`, unsupported, no mapped test),
fixed in `ac3a71d`. A mapping audit read 87% populated across 149 test
judgements, so the run was not half-blind and the rest could not be waved off as
blindness; those 18 trace to plainly unrelated tests in the mapped sets (#173),
with the rating movement itself recorded against #191.

Full triage in `../195-gate2-run3/judgement.md`.
