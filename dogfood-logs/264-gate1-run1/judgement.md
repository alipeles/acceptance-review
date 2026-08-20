# Judgement — #264 Gate 1, run 1

**Command:** `.venv/bin/acceptance decompose --task current-task.md --mode record`
**Run id:** `e28c217866839a10`
**Branch:** `264-per-stage-usage`, at `c652ab4` (no code changes yet).

`output.log` here is the console output as it was produced; it was transcribed
from the session rather than redirected, because the redirect was only set up for
run 2. `current-task.md` here is the exact input that produced it.

## Result

28 requirements, 27 with obligations, 1 deliberately none. **Zero open questions.**

The one requirement deliberately given no obligation is `[completion-01]
Implementation` — a bare section marker. Declining it is correct.

## What was real, and what was a tool defect

**No tool defects found.** Two findings, both attributable to the task file's
wording, and both fixed there. The rewrite is the sanctioned one (CLAUDE.md
invariants: fix the wording, never the output).

### 1. `exclusion-05` was read backwards — real, my wording

Input: *"The price of a token, which the provider's own accounting supplies."*

Derived: `exclude-token-price-recomputation` — *"The change excludes **using the
provider's own accounting to supply** the price of a token."*

That inverts the intent. The exclusion means *we do not compute token prices
ourselves, because the provider's accounting already reports the cost*. The
decomposer attached the exclusion to the wrong half of the sentence, and the
sentence genuinely admits both readings — a non-finite relative clause hanging off
a bare noun phrase, with no verb saying what is excluded.

Rewritten to: *"Computing the price of a token, which the provider's own
accounting already reports for each call."* Run 2 derived
`no-token-price-computation` — *"The change does not compute the price of a token
beyond the provider's own accounting for each call."* Correct.

### 2. `exclusion-01` turned an excluded activity into a required property — real, my wording

Input: *"Reducing what a run costs, and changing how much of a prompt the provider
serves from its cache."*

Derived: `no-run-cost-or-cache-share-change` — *"The change **does not alter** what
a run costs or how much of a prompt the provider serves from its cache."*

Also a defensible reading of what was written, and also not what was meant. The
intent was that *optimisation work* is out of scope (that is #265), not that the
delivered change must provably leave run cost unaltered — a property this change
cannot guarantee and no test should assert.

Rewritten to: *"Any work to make a run cheaper, and any work to increase how much
of a prompt the provider serves from its cache."* Run 2 derived
`no-run-cheaper-or-more-cache-work`. Correct.

## Not a defect: obligation ids differ between run 1 and run 2

Every obligation id changed between the two runs even for requirement text that
did not change (`every-model-call-records-issuing-stage` became
`call-records-issuing-stage`, and so on). This is the known instability behind
#193/#251 and is *not* a new finding — and #284, which landed immediately before
this task, is the mechanism that prevents it: run 2 was invoked **without**
`--continue e28c217866839a10`, so it reported `28 derived, 0 carried` and re-derived
everything from scratch. Carrying forward was available and was not asked for.

Worth remembering for Gate 2: pass `--continue` when the intent is to re-review
the same task file.

## Disposition

Gate 1 **not** passed on this run. Two wording corrections made, which re-arms the
gate. See `dogfood-logs/264-gate1-run2/`.
