# Judgement — #202 Gate 2, run 3

`acceptance check --task current-task.md --base 4ec4470 --head 31cc2e1`.
Re-run after addressing recommendation 3, per the re-arming rule.

**Verdict: INCOMPLETE. Not clean. And I am stopping here rather than editing
`current-task.md` a third time.**

## Where it landed

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| requirements | 47 | 52 | 52 |
| yielded an obligation | 46 of 47 | 42 of 52 | 42 of 52 |
| obligations | 35 | 36 | 36 |
| coverage gaps | 4 | 0 | **1** |
| strongly supported | 27 of 35 | 33 of 36 | **34 of 36** |
| recommended tests | 8 | 3 | **2** |
| unaccounted / unread | 0 / 0 | 0 / 0 | 0 / 0 |
| scope exclusions yielding | 10 of 10 | 1 of 10 | **1 of 10** |

The two remaining recommendations are both **#213** — the evidence is #195's
existing green suite and the tool cannot read it. Recommendation 3 is gone;
`tests/test_decision_records.py` addressed it.

## Finding 1 — the tool caught a third inaccurate scope claim, and it is right

The one coverage gap:

> *The diff preserves the existing obligation derivation path in broad terms, but
> it also changes the prompt shape, parse completeness, and reconciliation logic,
> so the derivation is not wholly unchanged.*

Against `exclusion-01`, which I reworded during run 2's correction to read:

> *Changing how obligations are derived from the requirements the model is shown.
> The derivation is untouched; what changes is which requirements reach it.*

**That is false, and the tool is right.** This change added two substantial
sections to the decomposition system prompt — *ACCOUNTING FOR EVERY REQUIREMENT*
and *REFERENCES YOU CANNOT RESOLVE*. Those unambiguously change how obligations
are derived, not merely which requirements reach the derivation. The second
clause of my own exclusion is contradicted by the diff it is supposed to bound.

## Finding 2 — the pattern across three runs is the real result

| run | the claim I made | the tool's finding | correct? |
|---|---|---|---|
| 1 | *"This change is representational"* | it also changes parsing, prompt shape, report structure | **yes** |
| 2 | *"The derivation is untouched"* (reworded) | it also changes prompt shape, parse completeness, reconciliation | **yes** |
| 3 | — | — | — |

Three Gate 2 runs, three scope claims, **two of them false and both caught.** The
tool is iterating me toward an accurate statement of what this change does, and
it has been right every time.

That is the single strongest result the tool has produced against its own
development. It is also uncomfortable in the specific way it should be: each
false claim was written by me *in response to the previous finding*, which is
exactly the drift the standing invariant exists to prevent.

## Why I am not editing the task file again

`current-task.md` has now been edited once in response to a Gate 2 finding. That
edit was authorised, the issue was amended first, and the reasoning is on #202.
But it produced a new false claim, which produced a new correct finding.

A third rewording would make the gap disappear. It would also be the third
consecutive edit to the checker's input made after seeing what the checker said —
and at that point *"never edited to change what the review says"* has been
violated in substance whatever the justification for each individual step.

**The finding stands as a true positive.** The honest options are:

1. **Accept the residue.** The gap is real, it is accurately described, and the
   review is correct to report it. Ship with it recorded, as #190 and #195 shipped
   with #153 residues.
2. **Amend #202 again** to state plainly that the change alters derivation — the
   prompt rules are part of the deliverable — and let `current-task.md` follow the
   issue. Defensible, since the prompt work *is* mandated by deliverables 1–4 and
   the exclusion was never accurate. But it is the same move a third time.
3. **Split the branch** so the prompt rules ship separately from the mapping.
   Genuinely narrows the change, and is the only option that makes the exclusion
   true rather than making it go away.

I have a preference — option 1 — but this is not my call, and the reason it is
not is that I am the party with an interest in the gate turning green.

## Finding 3 — the scope-exclusion decline is stable within a task-file version

1 of 10 in both run 2 and run 3, over the same task file, at different head
revisions. So this is **not** run-to-run nondeterminism: it flipped when the task
file changed (10 of 10 → 1 of 10 on six added bullets) and has held since.

That is consistent with #193's characterisation — sensitivity to input
perturbation rather than pure nondeterminism — and it is a slightly more
tractable defect than a coin flip. Recorded on #193.

## Disposition

| finding | disposition |
|---|---|
| 1 — `exclusion-01` still false | **true positive. Human decision required; not editing again** |
| 2 — three claims, two false, both caught | no action; the strongest positive result so far |
| 3 — decline stable within a version | recorded on **#193** |
| recs 1–2 | **#213**, filed, deliberately not satisfied with duplicate tests |

## Gate status

**Not clean.** Residue: one true-positive coverage gap about my own scope
statement, and two obligations attributed to #213.

Nothing here is a tool defect except #213. The gate is doing its job, and the
thing it is blocking on is real.
