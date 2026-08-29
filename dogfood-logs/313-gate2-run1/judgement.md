# #313 Gate 2, run 1 — judgement

**Not clean.** The verdict is `UNABLE-TO-DETERMINE`, on one obligation of
twenty-eight whose test evidence came back `indeterminate`. Gate 2's
clean-or-stop rule is suspended while #312's sub-issues land, so this is one run
and it is not iterated.

Command: `.venv/bin/acceptance check --task current-task.md --base ddb26c2 --head f2673fa --mode record --continue 3d391de59262b762`
Run id: `68d1e6a6621eab41`. `--mode record` because #317 orphaned the
decomposition corpus and this branch's new stage has no recordings at all.
46 live calls, $0.42, of which 24 calls and $0.25 are the new enumeration stage.

## What is clean

Every one of the twenty-eight obligations is `addressed` on the code axis or
recorded as not requiring code evidence. Twenty-seven of twenty-eight are
`strongly supported` on the test axis or recorded as not requiring test evidence.
**No open questions.** No `not_addressed`, no `unclear`.

The decomposition carried whole from Gate 1's run 5: zero decompose calls.

## The one indeterminate, and why it is a known defect rather than a new one

`pre-test-failure-modes` — task-01's obligation, *"Before any test is looked at,
record for each criterion derived from the mandate the concrete ways the
delivered code could plausibly fail that criterion"* — has no mapped test.

The evidence exists. `tests/defects/test_enumeration.py::test_the_enumerator_is_given_no_test`
asserts on the request as sent that no test file reaches the prompt, and
`::test_the_pipeline_really_calls_the_enumerator` asserts a real `run_review`
produces defect sets. Both were discovered, and both were mapped — to obligations
23 and 15, the `test_demand` twins of this one, and not to this one.

That is the open blocker about unmerged twin obligations starving each other of
mapped tests, already measured twice: task-01's behaviour obligation and
`completion-02`'s test demand are about the same property, linking did not merge
them, and the mapped test landed on the twin. Nothing new to file, nothing to
work around.

Read the recommendation before judging it, per the gate's own rule. It asks for
a test that *"the review output includes failure-mode notes for each derived
criterion before any test results are examined"* — a claim about report
ordering. The test already written asserts the stronger property, on the request
the stage actually built, which is where test-blindness can be broken.

## Ten unrequested changes, and four of them are correct

Findings 1, 2, 6 (`risky`) and 10 (`separable`) are the #317 stage-attribution
fix rolled into this branch: `align_obligations` gaining a `stage` parameter,
`plan_carry` passing one, `run_check` carrying defect sets into the ledger, and
the two tests that cover it. **The tool is right.** None of that is in this
mandate; it is here because the human asked at Gate 1 for the newly-found defect
to be rolled in rather than filed. A true positive about a deliberate decision,
recorded rather than suppressed.

The remaining six are `in_service` and correctly so — the new package, the
pipeline insertion, the report block, the state models, the ledger fields and
the test-double default all serve obligations the mandate states.

## The new advisory section, on its first real run

It ran over all twenty-two enumerable obligations and produced typed, located
candidate defects. Worth recording what it got right and wrong, since it is the
thing being built.

**Right, and deliberate:** `pre-test-failure-modes/defect-stage-not-invoked-for-all-derived-criteria`
observes that `enumerate_defects` skips obligations `enumerable()` rejects. True.
That is DR-313 decision 2, and the stage is doing what it should — enumerating a
plausible failure, not asserting it is present.

**Wrong, and correctly shaped anyway:** `recorded-failure-fields/non-unique-defect-ids`
claims two defects from different obligations could collide, because
`_defects_from` de-duplicates only within one answer. They cannot: the id is
`{obligation.id}/{slug}`, and two obligations have different ids.
`test_every_defect_id_is_unique_within_the_review` covers it. A candidate defect
that turns out to be absent is the expected output of a stage that enumerates
rather than judges — the whole point of the pair-mapping sub-issue that follows.

Both are typed against the criterion's own checklist and both cite hunks, which
is the shape the design asks for.

## Disposition

Move forward. Nothing here identifies a defect in the delivered work: the one
indeterminate is a known mapping failure with the evidence already written, and
the unrequested changes are an accurate report of a deliberate, instructed
decision.
