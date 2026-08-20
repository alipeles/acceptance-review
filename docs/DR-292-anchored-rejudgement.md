# DR-292 — Showing a judge its own prior answer, when the answer is ordinal

**Issue:** #292 (child of #183). **Status:** resolved, implemented.
**Related:** `DR-269`, `DR-180`, #286, #293, #251.

## The decision

A criterion whose inputs changed is re-judged **with the rating the previous
review recorded and the specific changes to that criterion's dependencies**, and
a judgement that moves the rating must name one of those changes. The rejection
is performed by the code that reads the response, not by the instruction that
asked for it.

## Why this is not the anchoring `DR-269` refused

`DR-269` deliberately kept decomposition's own previous answer away from the
model — *"anchoring bias is defeated by not asking"*. This decision shows the
model its previous answer. That is a real tension and it is worth being precise
about where the line falls.

**An evidence class is ordinal; a decomposition is not.** The §9.3 classes run
`unsupported < indeterminate < nominally < partially < strongly supported`, so
"this got worse" is a claim with a direction — it can be stated, interrogated,
and required to have a cause. Decomposition's output is a *set* of obligations
with no order over it, so there is no corresponding claim to interrogate: an
obligation set that came out differently is simply different, and the only honest
protection is not to show the previous one at all.

So the rule this establishes is narrower than "show the prior answer":

> Show a prior answer only where the answer is ordered, and only together with
> the changes that could justify moving along that order.

#286 asks whether justification generalises beyond ordinal outputs. This is the
first real answer and it is a **qualified no** — the mechanism works here
*because* the output is ordinal, and nothing here shows it would work where it
is not.

## Why the enforcement is in the reader

The prompt does ask the judge to justify a move (`_ANCHOR_INSTRUCTIONS`). That
alone would be worthless: a prompt is advice, and this whole project exists on
the premise that a claim without discriminating evidence is not evidence. The
constraint is therefore expressed three times, in increasing strength:

1. **The prompt** asks for `rests_on` when the rating moves.
2. **`supplied_ids.constrain`** puts the supplied change ids into the response
   schema as an enum, so a change the judge was not given is *unrepresentable*.
3. **The reader** applies the M5.3 reduce to the fresh defects, compares the
   resulting class with the stored one, and rejects a move that rests on nothing
   it was given.

Only (3) is load-bearing, and (2) cannot replace it: `constrain` takes a flat
field→ids mapping, so the enum is the **union** of every change id supplied to
the call. A criterion can name a change belonging to a different criterion in the
same batch and still satisfy the schema. The per-criterion check has nowhere to
live but the reader.

## The wrinkle: the judge does not return a rating

`judge_discrimination` returns *defects*. The rating is
`strength.py::classify_strength`'s deterministic reduce over them, so whether a
judgement "alters the rating" is only knowable after that reduce.

The reduce could not simply be imported into the reader: `strength.py` imports
`ObligationDiscrimination` from `discrimination.py`, so the import would close a
cycle. Re-deriving the arithmetic in the reader was the alternative and is worse
— two copies of the §9.3 bright line drift, and the copy in the reader would be
deciding whether to reject a judgement on a rule the classifier no longer used.

So the reduce was lifted into `evidence/classification.py::evidence_class_for`,
which both callers are downstream of. There is still exactly one bright line.

## Granularity: coarse, and deliberately temporary

A criterion depends on its requirement text, the tests mapped to it, and those
tests' contents. Comparing test **contents** is #293's deliverable and does not
exist yet, so the changes named here are file-level: which files holding this
criterion's mapped tests or implementation were touched, plus a reworded
requirement. #293 sharpens them without changing this decision.

**A criterion with no nameable change is not anchored at all.** This is the
non-obvious half. Anchoring such a criterion would make its rating *unmovable* —
with no change to rest on, every move is rejected forever — and the file-level
view cannot yet see a change that is real but sub-file. Freezing a rating we
cannot explain is the same failure as moving one we cannot explain, pointing the
other way. So the anchor applies only where there is something to name.

## The rule is symmetric, and that was decided deliberately

A rating that moves without resting on a supplied change is held **whichever way
it moved**. Raising and lowering are treated identically.

This was questioned at #292's Gate 2 and settled by the owner on 2026-08-20. The
question was whether a *falling* rating should be let through unjustified, on the
grounds that `DR-180` found the low rating correct in 7 of its 8 unstable
obligations — so a fall is usually the judge finally noticing a real hole.

**That argument was rejected, and the reasoning is worth keeping.** It confuses
two problems:

1. **A prior judgement must not move without a changed input.** This is the rule,
   it applies everywhere in the pipeline, and it has no direction-dependent
   exception. A rating that falls for no stated reason is exactly as untrustworthy
   as one that rises for no stated reason — in both cases the verdict is a
   function of how many times the obligation was looked at.
2. **The first judgement should be right more often.** This is `DR-180`'s actual
   finding: the tool errs toward "looks fine", and issues `strongly supported`
   where it was not earned. That is a real and serious problem.

Letting unexplained falls through would be using (1) to paper over (2): accepting
instability as a repair mechanism for bad first judgements. It would make the
tool's output depend on how many times it was run, which is the thing this issue
exists to stop. (2) is owned separately, under #183 and `DR-180`.

The consequence is accepted with open eyes: where the first pass issues an
unearned `strongly supported`, this rule can hold it against a later, better
judgement that fails to name a cause. The answer to that is to fix the first
pass, not to reopen the door.

## What this must not become

`DR-180`'s central finding is that the instability is **not symmetric noise**: in
7 of the 8 unstable obligations, the LOW rating was the correct one. Ratings that
fall are usually the judge finally noticing a hole that was always there. A
"stability" fix that damps the judge would lose every one of those, and #191's
measurement shows how easy that is — the pre-change judge answered
`would_be_caught: true` to 114 of 114 defects.

This decision is therefore **not** a damping mechanism. It does not make the
judge more reluctant, and it does not touch which defects the judge names. It
refuses exactly one thing: a rating that moves for no stated reason. A rating
that moves because the tests genuinely changed is accepted, and
`tests/fixtures/rating-stability/` is the standing check that the findings
recorded there are still found.

## Cost

Only re-judged criteria carrying a stored rating get a new request key: the
anchored call uses a distinct response model (`_AnchoredDiscrimination`) and an
extended system prompt, and the schema name is hashed into the key. A review with
no stored earlier state sends byte-identical requests to what it always sent, so
existing transcripts still replay and a first review pays nothing for a feature
it cannot use.
