# Judgement — #314 Gate 1, run 3 — the run Gate 1 passed on

Continuing run `18008963f6b28faa`. Two edits since run 2: the redundant
`constraint-08` deleted, and `constraint-09` split into its two directions.
29 requirements, 28 with obligations, one deliberately none. No open questions.

## What the two edits fixed

**The deletion was handled correctly.** The run reports `REMOVED constraint-08 …
(1 obligation(s) dropped)`, and `constraint-06` kept its own obligation — no
collateral loss. This is the shape #306 gets wrong (a continued run keeping an
obligation whose source sentence was deleted); here it worked.

**The split produced both directions.** `reuse-entitled-verdicts-on-continuation`
and `reproduce-only-nonreusable-verdicts-on-continuation` are both in the
obligation set, so over-carry and under-carry are each demanded. One oddity, not
a loss: `constraint-08` is given both obligations where it states only the first,
so the second is attached to a requirement that does not state it. Noise, since
the demand it belongs to (`constraint-09`) also carries it.

## Confirmation

I confirm this decomposition is accurate: every demand in the mandate is present
as an obligation, and no obligation states anything the mandate does not. The one
qualification is the two obligation-type slips below.

## Attributed to a known tool defect, unchanged from runs 1 and 2

`completion-06` typed `functional` rather than `test_demand`, and `completion-07`
merged into `constraint-11`'s `functional` obligation with no test demand of its
own. Both behaviours are still demanded — as functional obligations — so what is
lost is the demand that a *test* assert them, and both are on #314's own
Acceptance, so the tests get written regardless. Fourth and fifth instance of the
queued defect *"Two obligation-type slips, one of which loses the `test_demand`
distinction DR-232 exists to carry"*, drafted for filing as a comment on #181.

No open questions on any of the three runs — see run 1's judgement and #303.
