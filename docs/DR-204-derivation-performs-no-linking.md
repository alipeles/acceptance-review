# Decision Record 204 — Obligation derivation performs no linking

*Relates to issue #204 and the #181 umbrella (decomposition), with consequences
for #144, #211, #210 and #223. Status: **accepted, not built**. Track: checker.
Stage: 1. Partly reverses DR-202 decision 2, on evidence DR-202 did not have.*

---

## The decision

**Obligation derivation performs no linking.** A derivation call may split one
requirement into several obligations, or decline it with `no_obligation`, but it
may not attach a requirement to an obligation derived from a different
requirement. Every obligation it produces is named by exactly one requirement.

**The many-to-one mapping becomes de-duplication's output (#144), not
derivation's.** #202's model — an obligation may serve several requirements — is
unchanged as the *final* state of a review. What changes is which pass is allowed
to create it.

Sequencing: #216, then #204 carrying this rule, then #144 immediately after.

## What forced it

Derivation-time linking failed in both directions on the same corpus, under the
same code, model and seed.

| run | failure |
|---|---|
| #216 Gate 1 run 1 | Seven scope exclusions **declined** `no_obligation`, with reasons that stated the obligation (#219) |
| #216 Gate 1 run 2 | All five scope exclusions **over-merged** onto another requirement's obligation (#210, 5 of 5); two Constraints absorbed into an obligation stating neither (#223) |

The second is the worse one. `constraint-11` — *"Typed schemas are pydantic
models"* — was dispositioned `yielded` onto an obligation reading *"A test
asserts region-level total coverage over the repository's committed task files
and over the decompose-stability corpus."* The words "pydantic" and "live model
calls" appear nowhere in any of the thirteen obligations produced. The
requirements' content is gone, and the run reports `with obligations: 28`,
counting them as read.

That is the same failure #216 itself is about — content lost under a clean bill
of health — one layer above the parse. `with obligations: N` counts
**dispositions, not coverage**.

## Why this partly reverses DR-202 decision 2

DR-202 decision 2 argued that the requirement → obligation mapping *avoids*
over-merging by anchoring the judgment to identified requirements: shifting it
from the fuzzy *"are these two obligations the same?"*, whose worst outcome is
over-merging, to the anchored *"does this requirement restate one already
covered?"*.

#210 established that this **relocated** over-merging rather than removing it —
from de-duplication into linking. This decision moves it back, deliberately, on
three grounds DR-202 did not have.

**1. Lossy versus noisy.** Over-merging at derivation destroys a requirement's
content, as `constraint-11` shows. Under-merging in a de-duplication pass leaves
two obligations saying nearly the same thing: verbose, more downstream calls,
nothing lost. #144 already mandates *bias toward under-merging* for exactly this
reason. Derivation carries no such bias, because it is not framed as a merge
decision at all — the model is enumerating, splitting, quoting and linking in one
response, and linking is the field that loses.

**2. Attention — the #205 precedent, applied a second time.** #205 pulled
obligation typing into its own pass on the finding that a judgment *"asked as a
field on a response that is simultaneously enumerating, splitting and quoting
loses to everything else competing for attention."* Linking is another such
field on the same response, and fails the same way.

**3. It is now measurable.** #211 scores link precision separately from coverage.
The previous relocation had no measure, and #210's caveat stands: nothing here
should be judged by inspection.

## Why partitioning alone is not enough

#204's partitioning makes cross-batch linking structurally inexpressible — ids
originate per call. That covers **every** mis-link observed in #216's run 2: each
spans requirement positions falling in different batches at any reasonable size.

| mis-linked requirement | position | obligation derived from | position |
|---|---|---|---|
| constraint-11, constraint-12 | 16–17 | completion-05/06 | 27–28 |
| exclusion-04, exclusion-05 | 21–22 | task-03/04 | 3–4 |
| exclusion-01, exclusion-03 | 18, 20 | task-01/02/05 | 1–5 |
| exclusion-02 | 19 | completion-07 | 29 |

But batches are **contiguous runs of requirements**, so within a batch every
requirement is lexically adjacent to every other — precisely the condition #210
identifies as the over-merge trigger. Partitioning alone removes the mis-links
that are easy to catch by eye and leaves the highest-risk region untouched, which
is worse than it sounds: the remaining failures look like a clean result.

## Mechanism — a validator, not a prompt rule

> Within a derivation response, each obligation id appears in exactly one
> requirement's disposition.

A response naming one obligation from two requirements is rejected through
`UnusableAnswerLog`, in the shape #204 already specifies for a returned id that
was not supplied, and neither requirement is treated as disposed. Cross-batch
linking needs no check at all.

This is deterministic and post-response. That matters: every prompt-level rule
considered for #210 depends on the model honouring it, and #219's evidence is
that the decomposer already violates an explicit instruction at
`obligations.py:150`.

## Consequences

- **#204** gains the rule and its validator.
- **#144** gains linking, and its load grows substantially. On #216 run 2's task
  file the pre-merge set would be roughly 29 obligations against the 13 produced
  — about 16 merges, well beyond the 15-obligation scale its context section
  describes. Whether that pass itself needs partitioning becomes a live question.
- **#211** must score link precision over **#144's output**, not the derivation
  pass, where after this change it is undefined. The measure moves; it does not
  disappear.
- **#210 and #223** stay open as the evidence, and close when #204 and #144 have
  landed and #211 scores them — not on the strength of this decision.
- **Cost between the two landing.** Every downstream stage is per-obligation, so
  an unmerged set roughly doubles model calls and report length. #204 and #144
  must be sequenced adjacently, and neither should sit half-landed on `main`.
- **Re-record.** Both force one, and both make `decomposition_accuracy`
  non-comparable across the change.

## Measurement

- A derivation response naming one obligation from two requirements is rejected
  and recorded through `UnusableAnswerLog`.
- A requirement stated twice in a task file yields two obligations from
  derivation, and one obligation with two requirement links after
  de-duplication.
- `constraint-11` and `constraint-12` from `dogfood-logs/216-gate1-run2/` each
  yield an obligation stating their own content.
- The five scope exclusions from that run each yield their own obligation stating
  what is not done.
- Link precision is reported over the de-duplication output and scored through
  #211, not by inspection.

## What this does not settle

Whether an obligation needs test evidence at all is #148, and `constraint-11` is
its canonical case: *"Typed schemas are pydantic models"* is settled by reading
the diff, not by a test. A hypothesis recorded on #223 — that derivation is
oriented toward testable behaviour, so a code-evident requirement gets absorbed
into a test-shaped obligation — would make #148 and #223 the same root cause seen
from two ends. It is unproven, and `constraint-12` is test-evident and was
absorbed too, so it cannot be the whole explanation.
