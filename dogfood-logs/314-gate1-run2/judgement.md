# Judgement — #314 Gate 1, run 2

Re-run after rewording `constraint-08`, continuing run `4b3035551e18fd72`.

**The rework did not change the outcome, and that settled the attribution.**
`constraint-08`, reworded to "A verdict's reuse is decided from the way of
failing and the test it concerns alone. No other pair judged alongside it bears
on that decision", was attached again to `constraint-06`'s obligation. On
re-reading both bullets, the merge is right: `constraint-06`'s "reused exactly
while both are unchanged" already forbids a batch-mate affecting reuse, so the
two state one demand. The bullet was redundant wording of mine, not a
decomposition defect, and it was deleted for run 3. Run 1's judgement is
corrected accordingly.

**Carry behaved as #269 requires.** 28 requirements carried, 1 revised, on a
single decompose call against run 1's 29 calls. Every obligation not touched by
the reworded bullet was reused rather than re-derived, so the comparison between
runs 1 and 2 isolates the rewording.

**Both obligation-type slips reproduce unchanged** — `completion-06` typed
`functional`, `completion-07` merged into `constraint-11`'s obligation. Recorded
against the existing queue entry; see run 1's judgement.
