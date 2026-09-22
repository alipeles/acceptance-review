# Comment-and-whitespace gate, Gate 1 run 2 — judgement

Run `6b9fc74b0f155303`, continuing `af4321d0ce826ec8`. 8 live calls, $0.0277.
Worktree `refuse-comment-only-edits` at `768b0d7`.

**Accepted, subject to the human's confirmation.** 7 obligations over 6
requirements. Nothing invented, nothing missing, zero open questions.

Both of run 1's problems went away after the rewrite. The Constraint now yields
`no-model-in-refusal`, and the run reported the old one's removal explicitly —
`REMOVED constraint-01: No model is asked. (0 obligation(s) dropped)`, correctly
zero, since it had produced none. The context sentence is gone with the clause
that carried it.

## One thing to watch at Gate 2

The surviving obligation for the first requirement is
`reject-comment-or-whitespace-only-edits`, described as *"The review refuses an
edit that differs from the text it replaced only in comments or whitespace."*

**The word "always" did not survive into the description**, though it is the
whole reason this task exists: today that refusal happens only when the review is
also checking whether an edit makes its defect true, and the change is to make it
unconditional. Two merged-away siblings were named `always-refuse-…`, so the
decomposer did see it.

The risk is concrete. If the evidence stage judges the description alone, a test
demonstrating the refusal with edit verification switched **on** satisfies it,
while the delivered behaviour that matters is the refusal with verification
**off**. The test must exercise the off case, and whether the review notices the
difference is worth reading carefully at Gate 2.

## Ledger check, and a correction to how I described it

9 derived, 7 printed, every derived id accounted for: the two absent ids are
`always-refuse-comment-or-whitespace-only-edits` and
`…-2`, both merged into the surviving obligation.

**The shorthand I wrote in `session-state/334.md` is wrong** — "subtract the
`merge_decisions` entries whose `same_requirement` is true" gives 6 here, not 7.
Merge decisions are recorded per *pair*, so a cluster of three obligations
records three decisions and removes two. The reliable check is to compare the
derived ids against the printed ones directly, not to do arithmetic on counts.
That note has been fixed.
