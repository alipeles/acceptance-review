# Judgement — #191 Gate 1, run 1

SHA `4e6c9af` (main, clean tree). `decompose --mode record`, log rebuilt
byte-identically with `--mode replay`.

## Headline

29 requirements, 28 with obligations, 1 deliberately none. **One obligation per
requirement, no merging, no composites, no spurious links, no open questions,
no unreconciled cluster.** The cleanest Gate 1 decomposition in this repo's logs
— #259's produced 35 obligations for 33 requirements with three composites.

## Accuracy — confirmed, with one drift

Every one of the 28 obligations restates its own requirement and no other. Two
things the decomposer got right that it has previously got wrong:

- **Anaphora resolved.** `constraint-04` ("That number of obligations is
  configurable") and `constraint-05` ("That number ... is part of the recorded
  request") both bind "that number" back to `constraint-03`'s bounded count,
  rather than emitting a dangling referent.
- **`completion-01` "Implementation"** is dispositioned *deliberately no
  obligation* — "section marker standing alone with no requirement under it".
  Correct, and the disposition #237 exists about.

**The one drift — `constraint-11`.** Requirement: *"The change does not reduce
the defects the tool identifies."* Obligation: *"The change preserves the number
of defects the tool identifies."*

One-sided became two-sided. "Does not reduce" permits finding **more** defects,
which is the desirable direction and the whole point of DR-180's *stability must
not be bought by blunting the judge*. "Preserves the number" forbids it, and an
obligation that forbids improvement is one a correct implementation fails.
Filed as a queue entry against #181 rather than rewritten, because the source
wording is not weak — "does not reduce" is unambiguous, so this is the
decomposer losing a quantifier, not the task file inviting it.

## Open questions — none raised

Nothing to triage under the gate's three cases.

**This is the one thing I cannot confirm from a single draw.** #193 records that
open-question membership oscillates on unchanged input — present, present,
absent, absent, present across five runs — so "zero questions" is consistent
with both a well-specified mandate and the silent-drop failure #193 owns. A
second `--mode record` run would not distinguish them: the request key would
hash identically and replay, returning the same answer by construction. Telling
them apart needs #189's harness with the determinism controls off, which is
disproportionate for a gate check.

Recorded as an unresolved observation, not as a pass.

## Type assignment — inconsistent across structurally identical requirements

The six scope exclusions are typed `regression` twice (`exclusion-01`,
`exclusion-02`) and `functional` four times (`exclusion-03`…`06`), though all
six are the same construct. Their descriptions split the same way — "The change
does not alter X" versus "The change leaves X out of scope". Cosmetic here, but
it is #205/#196's subject matter observed on a fresh file. Queued, not blocking.
