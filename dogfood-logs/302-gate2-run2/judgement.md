# Judgement — #302 Gate 2, run 2

`acceptance check --task current-task.md --base 93740a9 --mode record --continue 094ddce626d72e7f`
Base `93740a9` (main, after #265/#293/#308 landed), head `11a8a5a`.
**Verdict: INCOMPLETE**, but far closer than run 1.

> 1 obligation(s) with non-discriminating test evidence
> (offer-reusable-request-when-provider-can-reuse).

## What run 1's three findings did on the rebuilt branch

- **#310's obligation is gone.** `exclude-measurement-harness-calls` no longer
  appears as `not addressed`. Nothing was done to it; the decomposer simply gave
  the exclusion the absence form this time. That is consistent with #310 being a
  *sometimes* fault rather than a deterministic one, and it means a single clean
  run is not evidence that #310 is fixed.
- **Both #245 twins are gone.** `test-fails-on-inconsistent-answer-formats` and
  `test-fails-on-withheld-conclusion-condition` are supported here. Again, nothing
  was done to them.
- **The `separable` finding is gone**, and this one *was* acted on: the wording
  fix now lives on `main` (`fec0b40`), so it is no longer in this branch's diff.
  All five unrequested changes are `in_service`.

## The one finding, and it is fair

`offer-reusable-request-when-provider-can-reuse` — *"A provider able to reuse a
repeated request is offered one"* — rated **nominally supported**. The
recommendation asks for a test showing that two calls a provider could reuse are
actually offered as reusable.

Read before judging, as the gate requires, and it is **correct**. The branch had
`test_every_batch_of_a_stage_asks_for_the_identical_schema`, which shows the
answer format is stable, and nothing showing the request *opens* the same way —
and the provider's cache key covers both. #265 landed tests about shared openings
(`tests/test_pipeline_request_openings.py`) but none asserting it for two mapping
batches, which is exactly what #302 delivers.

**Acted on, not attributed**: added
`tests/evidence/test_mapping.py::test_two_batches_of_one_run_offer_the_provider_the_same_reusable_opening`,
and verified by injection that restoring the per-batch enum fails it. That fix
re-armed the gate, and run 3 is the re-run.
