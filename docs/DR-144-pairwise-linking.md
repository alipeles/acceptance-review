# DR-144 — obligation linking sweeps every pair, and merges only confirmed cliques

*Decision Record. Status: **accepted**. Raised by #144. Amends the "do not
partition" decision recorded at #144's Gate 1. Related: #204, DR-204, DR-164,
#211, #212.*

## The decision

Obligation de-duplication asks the model one question per **pair** of
obligations — *do these two state the same requirement?* — sweeping every pair,
batched at `DEFAULT_LINK_PAIR_BATCH_SIZE`. Clusters are then computed from the
confirmed pairs, and a cluster is merged **only if every pair within it was
confirmed**. A cluster that is not fully confirmed merges nothing and is
recorded as an unusable answer.

## What it replaces, and why

The first implementation made one call holding all N obligations and asked the
model to report the duplicate pairs it found. That failed twice, on this
repository's own task file, in the same way:

| run | over-merge |
|---|---|
| Gate 2 run 1 | *"the links are typed fields"* merged with *"typed schemas are pydantic models"* — a behaviour and the library implementing it |
| Gate 2 run 2 | *"a test asserts a reason clause yields one obligation"* attached to *"a requirement stated in two sections yields one obligation"*, while its own rule sat unmerged beside it |

Run 2 followed a prompt change adding an explicit criterion for sameness, and it
is the more interesting failure: the criterion **forbade** the link it produced.
The two obligations hold under different conditions and are demonstrated by two
different tests that both exist in the tree. So the prompt was not
under-specified. The request shape was wrong.

Asking one call to find the duplicates among N obligations is an all-pairs
search — 276 comparisons at N=24 — and it degrades exactly as DR-164 measured
elsewhere: by shedding work rather than by failing. Worse, it is a *selection*
task. The model must choose a partner for each obligation, and a selection task
has no natural "none of these" answer, so it returns the nearest plausible
match. Both failures are that: not a wrong judgement about a pair, but the right
answer to a question we should not have asked.

Sweeping pairs removes the choice. Each judgement is one boolean about two
obligations, and `false` is as available as `true`.

## Why this is not the partitioning that was rejected

#144's Gate 1 rejected partitioning the obligation set, because a duplicate pair
landing in two different batches would be compared by neither call — silent
under-merging, indistinguishable from the bias working as intended.

Batching **pairs** has no such gap. Every pair is asked exactly once; the batch
decides only which call carries it. Completeness is preserved, which is the
property that decision was protecting. That decision is amended, not reversed:
its reasoning stands and rules out the thing it ruled out.

## Sameness is transitive; the model's answers are not necessarily consistent

The criterion is identical truth conditions — two obligations are the same if
they hold under exactly the same circumstances and one test demonstrates both.
That is an equivalence relation, so it *is* transitive. An earlier draft of this
decision claimed otherwise and could produce no counterexample; the claim was
withdrawn.

What is not guaranteed is that the model's **measurements** are consistent. It
can confirm A~B and B~C while denying A~C. Those are not an intransitive
relation — they are three answers that cannot all be correct.

This is the second argument for the complete sweep, and the stronger one.
Inferring A~C from the other two would not merely assume consistency; it would
**destroy the evidence** that consistency failed. Only asking every pair makes
the contradiction observable.

## The conservative rule

A connected component merges only if it is a complete clique. Otherwise no
member of it merges, and the component is recorded through `UnusableAnswerLog`.

Blunt, deliberately. Resolving a contradiction means choosing which answer to
believe, and every failure this pass has had has been an over-merge — so it
fails toward under-merging, the direction #144's bias accepts, and it says so
rather than deciding quietly.

The cost is that one contradicted pair discards the good merges in its
component. Accepted: those merges are recoverable on a later run, a wrongly
merged requirement is not.

## Consequences

- **Quadratic.** N=24 is 276 pairs, ~12 calls at 25 per batch. N=71 — #204's
  Gate 2 count — is 2,485 pairs and ~100 calls. Cheap against the downstream
  per-obligation work saved at today's scale, and not obviously cheap at
  tomorrow's. A pre-filter over candidate pairs would cut it, and would
  reintroduce exactly the invisibility this decision preserves against, so it is
  a separate decision and not taken here.
- `link_pair_batch_size` is a determinism control: only `size` enters the hashed
  request, never the batch index or count, exactly as `mapping_batch_size` and
  `decompose_batch_size` do.
- Pair enumeration and batch composition are pure functions of derivation order,
  so two runs over identical derived obligations produce identical links.
- The corpus now holds two linking recordings for one fixture, because the
  invoice task exceeds one pair-batch. Provenance markers in the manifest are
  fixture-level (`invoice`, `CSV`) rather than requirement-level: a pair batch
  contains only the pairs it was given, so a marker naming one obligation is
  absent from any batch that does not include it.
