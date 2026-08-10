# Judgement — #144 Gate 1, run 3

Run at `9724df4` (branch `144-merge-duplicate-obligations`). Third run; runs 1 and 2
are kept because the differences between them are the evidence for #231.

**27 requirements, 21 with obligations, 6 deliberately none, 24 obligations.
No open questions.**

## Accuracy — confirmed

All 11 Constraints and all 7 Completion expectations carry exactly one obligation.
Task prose yields two each. The six declines are the five Scope exclusions and
`[completion-01] Implementation`. Nothing real is missing, and nothing is invented.

## The declines improved between runs, which is itself the finding

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| requirements | 29 | 29 | 27 |
| with obligations | 28 | 28 | 21 |
| deliberately none | 1 | 1 | **6** |
| obligations | 30 | 33 | **24** |

In runs 1 and 2 each of the five `## Scope exclusions` produced an obligation, and
they were split two ways — three read as out-of-scope, two reframed as *"Preserve the
scope exclusion that …"* typed `invariant`. That inconsistency is filed as **#230**.

In run 3 all five are declined, uniformly, with one reason: *"This is a scope exclusion
naming work handled elsewhere, and it does not itself impose a checkable change in this
task."* That is the correct handling.

**The bullets did not change between run 2 and run 3.** Only `constraint-08` and
`completion-08` were removed, in different sections. So the behaviour on scope
exclusions moved from split-three-ways to uniformly-declined with no change to the
exclusions themselves. #230 should be widened: the defect is that exclusion handling is
*unstable across runs*, not merely inconsistent within one.

## Duplication persists, as expected — it is what #144 removes

24 obligations from roughly 15 distinct requirements. Eight clusters survive, all of the
Constraints ↔ Completion-expectations shape already recorded on the issue.

One is worth quoting because the model produced the evidence itself:

```
constraint-06 -> reason-clause-counts-as-same-requirement-2
completion-04 -> reason-clause-counts-as-same-requirement
```

The model minted the **same id twice** and the pipeline disambiguated with a `-2`
suffix. Two requirements it independently named identically are, by its own account,
one requirement — which is exactly the judgement #144's pass has to make.

## Task-file corrections made at this gate

Two, both sanctioned rewrites of weak wording:

1. `constraint-08` / `completion-08` first said *"obligations derived for a requirement
   change only when that requirement's own relevant inputs change."* Unachievable while
   DR-204 puts the whole registry in every derivation prompt — every requirement's input
   *is* the whole task file, which makes the rule vacuous.
2. Reworded to *"editing one requirement leaves the obligations derived for the other
   requirements unchanged"* — then **measured** against runs 1 and 2 and found false:
   a two-line edit re-split `task-01` and `task-02` and churned 27 of 33 ids.

Removed from this task file and filed as **#231** against the #184 determinism umbrella.
#144 builds the linking pass; derivation stability is not in its scope, and an acceptance
item the issue cannot reach is worse than none.

The determinism requirement #144 *does* carry is `constraint-10` — unchanged task text
yields byte-identical review state at both stages. That is buildable and tested here.
