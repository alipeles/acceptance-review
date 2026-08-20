# Judgement — #251 Gate 1, run 2

Re-run after run 1's two rewordings. 34 requirements, 33 obligations, one
requirement deliberately given none (`completion-01`, the bare `Implementation`
section marker).

**Result: not accepted.** Run 1's two findings are fixed; one new one.

## Fixed by the run-1 rewordings

- `completion-02`'s duplicate-description pair is gone: the split expectations
  each produced one distinctly worded obligation.
- `exclusion-05` now reads "Selecting which stored earlier state a repeated
  review continues is not part of the change" — correct.

## Finding 3 — a second Scope exclusion inverted, same shape

`exclusion-01` read "Partitioning the evidence-judgement request **so that one
criterion's request carries no other criterion's tests**." The obligation came
back as "The evidence-judgement request for one criterion carries no other
criterion's tests" — the exact opposite of what the exclusion says. The mandate
excludes partitioning, so the request will keep carrying every criterion's tests;
the obligation asserts it must not.

Same failure as run 1's `exclusion-05`: a trailing subordinate clause promoted
over the main clause, with the negation lost. Two instances in two runs of one
mandate.

**Disposition: task file reworded** to "Partitioning the evidence-judgement
request per criterion", **and queued as a tool defect** — this is the second
instance and it is now a pattern rather than a one-off.

## Not a finding, but recorded — the merge outcome this run

One requirement pair merged: `constraint-16` ↔ `completion-10`
(`byte-identical-review-state`). `constraint-01`↔`completion-02`,
`constraint-02`↔`completion-03` and `constraint-07`↔`completion-05` did **not**
merge, and the linking stage reported it could not reconcile a triangle among
`criterion-stored-rating-preserved-when-dependencies-unchanged`,
`unchanged-criterion-keeps-stored-rating` and `rejudge-only-on-dependency-change`.

Recorded because run 3 inverts it exactly — see
`dogfood-logs/251-gate1-run3/judgement.md`.

## Open questions

None raised.
