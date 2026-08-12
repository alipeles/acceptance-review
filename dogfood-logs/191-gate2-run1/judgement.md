# #191 Gate 2, round 1 — judgement

**Not clean.** INCOMPLETE: one obligation not fully implemented, three with
non-discriminating test evidence. No open questions. Seven unrequested changes,
two of them `separable`.

## The four negative findings — all real, all fixed in `8e49ead`

| obligation | finding | verdict |
|---|---|---|
| `test-verdict-call-carries-configured-bounded-obligations` | the test uses one defect per criterion, so batching by criterion and batching by defect volume are indistinguishable under it | **real** |
| `bounded-obligations-per-verdict-call` | same gap, stated against the behaviour rather than the test | **real** |
| `test-obligation-count-reaches-recorded-request` | partially addressed — the assertion reads the pile of transcripts, so it would hold on a verdict call that recorded nothing | **real** |
| `tool-identifies-no-fewer-defects` | nothing asserts the split loses no defect; the recommendation names the loss modes (a batch boundary, the id join, an unanswered verdict) | **real** |

The last one is the governing constraint of the whole change — *stability must
not be bought by blunting the judge* (DR-180) — and it was genuinely untested.
Splitting one call into two adds two places a defect can vanish, and a dropped
defect is invisible downstream because it looks exactly like a defect that was
never named.

Worth recording that this obligation is the one carrying the **`constraint-11`
quantifier drift** already queued against #181: the mandate says "does not
reduce", the obligation says "preserves the number". The drift did not stop the
recommendation from being correct and useful.

## Unrequested changes — the two `separable` ones are fair

1. `retake_baseline.py` — the baseline reproduction script. Genuinely not
   demanded by any obligation.
2. `_observed_discriminations` and the `embedding_model` forwarding in
   `instability.py` — the #189 harness fix.

Both are correct calls by the tool. They are the harness work that had to happen
before #191's baseline could mean anything, and under *one issue per branch and
PR* they belong in their own PR. Recorded rather than dismissed; the human's
call, since the harness fix is what makes the baseline this branch commits
trustworthy.

The five `in_service` ones are documentation, the CLI flags, the pipeline
signature and the test fixtures — all reasonable readings, none actionable.

## What this run does not settle

Round 1 says nothing about whether the *ratings* are stable, because there is
only one run. Round 2 is what shows that.
