# #350 — A defect the injector never attempted gets no pair-count line in the report

## What's wrong

#340, which uses injection results to route pair judgements, has this in its Deliverable:

> The report names, per defect, how many pairs the run settled, how many it routed to the judge, and how many it skipped.

That line is emitted only from `_mutation_block` in `src/acceptance/report.py`. A defect the injection stage never attempted — `not_mutable`, or `not_attempted` — has no mutation block, so it gets no line at all. The reader sees counts for some defects and silence for others, with nothing saying why.

Silence is the wrong output here. A defect no edit could be built for is exactly the case where every one of its pairs went to the static judge and none was dropped, which is worth stating rather than leaving the reader to infer from an absence.

This is not a rare corner on this repository. In #340's Gate 2 run 1, 39 of 68 attempts were `not_mutable` and 19 were `not_attempted` — the majority of defects produce no block.

## Where it was found

#340's own Gate 2 review raised two findings against this, `report-says-how-many-pairs-run-decided` and `put-to-the-model-count`. **Both stated the defect inaccurately**: they claimed the count is emitted only when a defect has a set-aside test, which describes an early return that `2f774c0` had already removed. This issue is the true version underneath, confirmed by reading `report.py` rather than by accepting the finding as written. Recorded in `dogfood-logs/340-gate2-run2/judgement.md`.

## Deliverable

Every defect the pair stage was asked about gets its counts in the report, including one with no injection attempt. A defect with no attempt shows zero settled, zero skipped, and all of its pairs put to the judge.

## Acceptance

- A test pins that a defect whose injection outcome is `not_mutable` or `not_attempted` still has its pair counts rendered.
- The counts for such a defect are correct, not merely present: all pairs put to the judge, none settled, none skipped.
