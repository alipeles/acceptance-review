# Judgement — #251 Gate 1, run 5

The mandate gained the carry-forward extraction: three Constraints and two
Completion expectations requiring the reuse rule to be defined once, stage-neutrally,
and reached by both decomposition and evidence judgement. Decomposed continuing run
3 (`da8f2ad18aec867f`).

```
run 13cbdc29e694e394
  continuing da8f2ad18aec867f
  requirements: 5 derived, 34 carried, 0 revised; 1 decompose call(s)
Requirements: 39   with obligations: 38   deliberately none: 1
```

**Result: accepted.** 39 requirements, 38 obligations, one requirement deliberately
given none (`completion-01`, the bare `Implementation` marker). Zero open questions,
as in every run of this mandate.

## The five new requirements decomposed cleanly

| requirement | obligation | type |
|---|---|---|
| `constraint-17` the rule is defined in one place naming no stage | `single-stage-neutral-carry-forward-rule` | invariant |
| `constraint-18` both stages carry forward through that definition | `decomposition-and-evidence-both-use-carry-forward-rule` | functional |
| `constraint-19` moving it changes no obligation decomposition produces | `moving-carry-forward-rule-does-not-change-decomposition-obligations` | regression |
| `completion-12` both decisions run through the same code | `same-code-path-for-carry-forward-decisions` | functional |
| `completion-13` an unchanged task file still issues no decompose call | `unchanged-task-file-no-decompose-call` | regression |

One obligation each, none invented, none missing, and the types are the ones the
requirements ask for — `constraint-19` and `completion-13` are both correctly
`regression`, which is what a refactor guard is.

## This is the first run to use `--continue`, and it worked

**34 of 39 requirements carried, 1 decompose call instead of 5.** Adding five
requirements re-derived only those five.

More to the point, the merge outcome held. Runs 2 and 3 inverted whether four
untouched requirement pairs merged when a single Scope-exclusion bullet was
reworded (see `dogfood-logs/251-gate1-run3/judgement.md` and `-run4/`). Here five
requirements were **added** and the three merges from runs 3 and 4 are all still
present:

- `constraint-01` ↔ `completion-02`
- `constraint-02` ↔ `completion-03`
- `constraint-07` ↔ `completion-05`

That is the `--continue` change in `CLAUDE.md` earning itself on its first use.

## The one residual redundancy, unchanged from run 3

The same unreconciled cluster, over the same three obligations:

```
affected: changed-rating-justifies-itself, changed-rating-names-one-given-change,
          changed-rating-must-name-a-change
```

One claim from three requirements (Task prose, `constraint-11`, `completion-07`).
Filed as a comment on #242. Not a stop: the gate's test is that nothing is invented
and nothing is missing, and a claim represented three times is neither.

## Open questions

None, across all five runs of this mandate.
