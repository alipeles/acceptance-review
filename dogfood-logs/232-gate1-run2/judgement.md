# Judgement — #232/#219/#230 bundle, Gate 1, run 2

First sanctioned rewrite: the `# Task` section restated as required behaviour
rather than as a narration of the defect. 23 requirements, 22 with obligations.
**No open questions.**

## Fixed by the rewrite

Run 1's `test-assertion-derives-behaviour-obligation` — an obligation to *perform*
the defect, contradicting `constraint-01` — is gone. Prescriptive prose does not
invert. Evidence for the #212 comment filed off run 1.

## Introduced by the rewrite

Three sentences of Task prose yielded **seven** obligations (`task-01` → 3,
`task-02` → 2, `task-03` → 2), all restating Constraints. Worse than run 1's
four. My wording, not a tool defect; run 3 tightens it.

## The apparent improvement in A is illusory

Four of run 1's five Constraint↔Completion merges did not happen. That is **not**
the linking pass distinguishing a behaviour from a test of it. The log ends:

```
Unreconciled linking answers: answers contradict each other: these obligations
are linked transitively but at least one pair among them was denied, so none of
them were merged
  affected: acceptance-criterion-test-obligation, behaviour-vs-test-distinct-requirements,
  test-demand-not-behaviour, behaviour-and-test-not-same-requirement,
  no-preservation-property-in-no-obligation-reason, acceptance-criteria-vs-behavior-distinction,
  test-demand-is-distinct-from-behavior, behavior-alone-does-not-satisfy-test-demand
```

An eight-obligation transitive cluster was contradicted, so #144's clique rule
merged nothing in it. The separation is a side effect of that suppression.

**Consequence for this task's own acceptance:** "no merge occurred" is not
evidence that the behaviour/test distinction is preserved. A test asserting
non-merger would pass today, for the wrong reason, and would keep passing if the
fix were removed. It must assert the *derived obligation demands a test*, not
that two obligations stayed separate.

## Unchanged — the defects this task exists to fix

Four of six scope exclusions still inverted (`exclusion-03`, `-04`, `-05`,
`-06`). `exclusion-01` and `-02` are correct in sense but changed type from
`human_review` (run 1) to `invariant`, on byte-identical bullet text — consistent
with #231, since the Task-section edit re-derives every requirement.
