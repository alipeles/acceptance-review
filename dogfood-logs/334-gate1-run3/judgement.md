# #334 Gate 1, run 3 — judgement

Run `a7f05ec002634926`, continuing `a1c00b42b03c0fb7`. **Zero decompose calls,
$0.0000** — 6 requirements carried unchanged, none derived, none revised. The one
call was an embedding for obligation linking. Worktree
`334-sample-candidate-edits` at `0b751b4`.

**Accepted.** 12 obligations over 6 requirements. Verified two ways: the printed
breakdown and the decomposition ledger agree at 12, which runs 1 and 2 did not
(see below).

## What changed

The compiled-form requirement was removed from the task file, on the human's
decision, after the measurement in `docs/experiments/334-bytecode-equivalence/`
showed that comparing compiled forms catches none of the three cases #334 names,
and that the class it does catch — comment- and formatting-only edits — is
already refused without a model call by the verifier #335 merged that morning.

The run reported the removal explicitly:

```
REMOVED task-02: The review also gains one further check … (3 obligation(s) dropped)
```

That count is correct, and tracing why it was correct is what turned up the
display defect below. Only 2 of those 3 obligations had ever been printed.

## The obligation set

Ask for several candidates; use the first that passes the checks the review
already applies; make the count configurable; fall back to today's handling when
none passes. Record per defect how many were asked for, how many set aside and
why, and which was used; report what building edits cost and how long it took.
Two runs over the same input pick the same candidate. Three Scope exclusions,
one obligation each.

Every behaviour in the mandate appears exactly once. Nothing invented, nothing
missing, zero open questions.

## The display defect, found here

The ledger and the printed breakdown disagreed in runs 1 and 2:

| run | ledger | printed | never printed |
|---|---|---|---|
| 1 | 25 | 24 | `compiled-before-after-comparison` |
| 2 | 15 | 14 | `compiled-before-after-compare-compiled-forms` |
| 3 | 12 | 12 | — |

Both hidden obligations are `importance: critical` and carry their own source
span. Both sit in the one requirement that also held near-duplicates; run 3,
which had none, hid nothing. **Hypothesis, not verified:** the renderer suppresses
one of a near-identical pair while the persisted set keeps both. The rendering
code was not read.

This is the reason run 2's judgement had to be corrected. It matters beyond this
task: Gate 1 is the human confirming the breakdown, every later stage judges the
persisted set rather than the printed one, and the two diverge precisely when
duplicates are present. Queued as a filing.

## Method note

Counts taken from `.acceptance/ledger/<run>.json`, field `derivations[].obligations`,
against `grep -c '^    -> ' output.log`. The ledger is per-run local state and is
not committed, so the figures above are the record.
