# DR-269 — a carried entry's validity key excludes the rest of the registry

**Issue:** #269 · **Status:** accepted · **Date:** 2026-08-19

## The rule as written, and why it cannot be implemented literally

#269's mandate says:

> An entry is carried only when re-deriving it would issue the same request key
> it was recorded under.

Taken at face value that is unimplementable in a useful form, and the reason is
#178. The decompose prompt carries **the whole registry** on every call — every
requirement's text, with the batch's ids marked `ANSWER FOR THIS` and the rest
marked `context only`. That is deliberate: a call shown only its own bullets
cannot notice that a later section settles a term an earlier one leaves open, and
#178 is the record of that failure.

So the real request key for any one requirement moves whenever **any other**
requirement is edited. Under the literal reading, a carried entry is valid only
when nothing in the task file changed at all — which is the one case where
carrying forward buys nothing, since an unchanged file replays from its
transcript for free anyway. Per-requirement carry-forward would be dead code, and
the mandate's own `constraint-04` — an edited requirement is re-derived while
others are carried — could never occur, because the edit that triggers it is the
same edit that invalidates every other entry.

The mandate contains both rules and they contradict each other. This records
which one wins.

## Decision

The **carry key** hashes only:

- the decompose system prompt,
- the unconstrained `_Decomposition` response schema,
- model, temperature, seed,
- the stage-logic version,
- **that requirement's own text**.

It does **not** hash the rest of the registry, and it does not hash the
constrained per-batch schema. (The batch constraint is excluded for a second,
independent reason: it is a function of how the run happened to be partitioned,
so hashing it would discard work when `--decompose-batch-size` changed, which has
nothing to do with whether the answer is still right.)

## What this costs, stated plainly

Because the model sees the whole registry, an unchanged requirement **could
legitimately decompose differently once its neighbours change**. Carrying it
forward suppresses that. A requirement whose meaning is genuinely altered by an
edit elsewhere — a later section that redefines a term it uses — will keep
obligations derived under the old reading, and nothing in the system will notice.

That is not a bug being tolerated; it is the trade the feature exists to make.
#191 measured what the alternative costs: three runs over one unchanged task
file, differing only by seed, produced 38 distinct criterion wordings across ~20
criteria — 8 appearing in all three runs, 23 in exactly one — with identifiers
re-minted alongside them and **zero obligation content difference**. Nothing was
being lost to re-derivation except stability, and criterion text is the prompt
for every later stage, so that churn floors every downstream stability number.

Suppressing a rare, real cross-requirement re-reading is the price of removing a
constant, measured, spurious re-wording. The judgement is that the trade is
strongly favourable, and it is reversible: including the registry digest in the
carry key is a one-line change if the cross-requirement case ever proves to
matter more than the churn.

## What still invalidates an entry, so the key is not doing all the work

Carrying is gated on four independent checks, and the key is one of them:

1. **Exact text match** of the requirement, against the continued run.
2. **Carry key equality** — this document's subject.
3. **Stage-logic version equality** — `DECOMPOSE_STAGE_LOGIC_VERSION`, bumped by
   hand, covering code changes that alter the output without changing the
   request. The request key cannot see those; nothing else can either.
4. **Source spans still present** in the new requirement text
   (`carry.py::stale_spans`), which is `_locate_quotation`'s rule applied to a
   carried entry rather than a freshly derived one.

## The consequence for cross-task contamination

Identity is the requirement's exact text, so a ledger recording an unrelated task
matches nothing and every requirement derives fresh. That is what makes #269's
acceptance item — *a decomposition run against a ledger recording a different
task file produces the same obligations as one run against no ledger at all* —
hold, and note that it holds by **identity**, independently of the lineage
signal. Two mechanisms, not one.

**The known boundary:** two task files sharing a byte-identical requirement — a
bare `- Implementation` bullet, say — will carry that one requirement across.
Text identity cannot distinguish "the same requirement" from "the same words",
and no threshold is available to help: DR-259's *"0.10 is a clean separator"* was
withdrawn and #211 exists to settle whether any threshold is defensible. The
residual risk is one carried obligation over a bullet whose wording is identical
in both mandates, which is bounded and visible in the ledger. It is recorded here
rather than fixed because fixing it well needs #211.

## Alternatives rejected

**Hash the whole registry.** The literal reading. Rejected above: it makes the
feature inert.

**Hash the registry but exclude requirements marked `context only`.** Does not
help — every requirement is `context only` to every batch but its own, so the
digest still moves for everyone when one bullet changes.

**Re-derive a carried requirement and compare, keeping the old id if the
substance matches.** This is what the previous shape effectively did, and it
costs a model call per requirement — the exact cost #269 exists to remove. It
also re-introduces the anchoring problem: showing the model its own prior answer
for approval is not a judgement, it is a rubber stamp.

## Related

#178 (whole registry as context), #191 (the churn measurement), #193 (the defect
report), #209 (requirement identity across versions), #211 (whether any
similarity threshold is defensible), DR-204 (derivation performs no linking),
DR-259 (the withdrawn threshold, and the cache clear that lost two runs).
