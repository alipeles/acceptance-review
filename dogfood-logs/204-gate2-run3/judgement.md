# Gate 2, run 3 — #204 at the schema change

The run **completes** — runs 1 and 2 could not. `INCOMPLETE`: one obligation not
fully implemented, 23 with non-discriminating test evidence, out of **71
obligations derived from 34 requirements**.

## The headline: Gate 2 cannot come back clean for #204 alone

71 obligations from 34 requirements is not a defect in this run. It is the
unmerged set DR-204 predicted, and reading the ids makes it plain:

```
partition-derivation-by-requirement-batch
partition-obligation-derivation-by-batch
partition-derivation-by-requirement-batch-2
use-existing-partitioning-mechanism
```

Four obligations, one requirement, restated across Task / Constraints /
Completion expectations. Likewise `byte-identical-review-state` and
`byte-identical-review-state-2`; `deterministic-merge-order-2`;
`preserve-disposition-for-every-requirement-after-merge-2`.

This is the intended output of #204 as amended: derivation gives every
requirement its own obligation and **#144 merges them afterwards**. Until #144
lands, every downstream stage judges the near-duplicates independently, so the
report is roughly twice the length and the same handful of gaps is counted many
times. Most of the 23 "non-discriminating" findings are one gap seen four ways.

DR-204 said this in advance:

> Every downstream stage is per-obligation, so an unmerged set roughly doubles
> model calls and report length. #204 and #144 must be sequenced adjacently, and
> neither should sit half-landed on `main`.

**So a clean Gate 2 is not achievable for this issue on its own, and chasing one
would mean merging by hand what #144 exists to do.** That is the finding, and it
is a sequencing fact rather than a defect.

## Two real findings underneath

**1. The decomposer turns the problem statement into a requirement (#212).**
Run 2 produced, from `task-01`:

> *"Perform obligation derivation with one model call for the whole requirement
> registry."* — `code evidence: not addressed`

`task-01` is the paragraph **describing the defect being fixed**. The decomposer
read it as a requirement to preserve the defect, then correctly reported the fix
as a failure to deliver it. This is #212 — *task files cannot distinguish context
from requirements* — and it is the cleanest instance of it yet: not background
becoming a harmless extra obligation, but background becoming an obligation that
**contradicts the mandate**, and turning a delivered change red.

Attributed to #212. Worth a comment there with this evidence.

**2. Verbatim response repetition, new since the schema change.** Run 3's first
attempt aborted with `requirement 'task-01' was disposed more than once`. The
transcript shows the model emitted its **entire disposition list twice**, byte
for byte — seven entries repeated, one of them carrying thirteen nested
obligations.

Plausibly a consequence of this change: nesting the obligations inside their
dispositions makes responses much larger, and long generations invite repetition
loops. Handled by dropping an **exact** repeat (it carries nothing the first copy
did not) while a duplicate that *differs* stays a rejection, since two different
answers for one requirement is the self-contradiction M1.2.r2 exists to catch.

Worth watching rather than closing: if it recurs at larger sizes, the batch size
is the lever.

## A mandate correction, stated plainly

`current-task.md` constraints 07 and 08 specified the **validator** mechanism —
*"each obligation id appears in exactly one requirement's disposition"*,
*"recorded through `UnusableAnswerLog`"*. That mechanism was replaced, by
decision, with a schema shape. The tool was right to report those constraints as
unaddressed: the change deliberately does not do what they describe.

They were rewritten to state the delivered contract. **This is updating the
mandate to the design that was agreed, not editing the output to match the
code** — the obligation being asked for is unchanged, and the rewrite makes the
requirement harder to satisfy vacuously, not easier.

## Standing

The implementation is complete against #204's deliverables and the suite is
green at 858. Gate 2 is honest but cannot be clean until #144 lands, which is
what DR-204 requires anyway. The remaining question is a sequencing decision for
the human, not a defect to patch.
