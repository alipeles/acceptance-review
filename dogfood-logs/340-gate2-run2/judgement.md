# #340, Gate 2, run 2 — still not clean, but the instrument now works

Run `b817a381ae99a035`, continuing run 1's `d175a70ee540e9e0`. base `f74a016`,
head `07d61a8`. **INCOMPLETE**: four criteria partially supported, four
recommended tests, nine unanswered pairs. Spent $2.5583.

Better than run 1 on every axis that was under my control: six failing criteria
down to four, and the report 156 KB instead of 768 KB.

## The evidence fix worked, in the real review

**5 candidate tests set aside, every one with its cause recorded**, against 76
with no cause in run 1. All five are the same thing:
`acceptance.benchmark.corpus.UnresolvableRevisionError: case '163-gate2-run1'
names revision '4d13ba1'`. They resolve a git revision and `copied_project`
leaves version-control history out, so they cannot pass in a copy. The control
check is doing exactly its job, and this is the first run in which a reader could
tell that without instrumenting the tool.

**The 75-failure mode did not recur** — six clean rounds now against two bad
ones, still unexplained.

## Where the rest of the saving goes, and it is self-referential

Run 1 had 18 `survived` attempts; this run has **19 `not_attempted`**, and the
reasons name the cause:

> no test went red, but 115 of 277 did not complete under the mutant
> (`tests/test_mutation_pipeline_wiring.py::TestAnAlreadyPresentDefect…`)

Roughly 50 of this repository's own candidate tests **run the review's execution
tier**, which spawns a nested pytest. Injecting a mutant into the tool destabilises
those nested runs, so 100 or more candidate tests fail to complete, and the runner
correctly refuses to read that as a survival.

**This is a dogfooding artefact, not a property of the product.** The tool is
mutating its own test harness. `CLAUDE.md` already warns that this repository is
the easy case and supplies counterexamples rather than thresholds; here it is
supplying a hard case that no client repository would have. Any figure for how
much routing saves, measured here, is depressed by it.

## The four findings

1. **`inject-edit-for-each-plausible-defect`** — unchanged from run 1, and still
   about the pre-existing injection stage rather than this change. It exists as a
   criterion only because my task file's opening sentence narrates behaviour the
   review already has.
2. **`report-says-how-many-pairs-run-decided`** and **`put-to-the-model-count`** —
   the stated defect is inaccurate. It says the count is emitted "only when a
   defect has at least one set-aside test", which is not what the code does; the
   early return was removed in `2f774c0` and `_pair_disposition` now returns a line
   for every rendered attempt. What is true underneath it: the line is only
   emitted from `_mutation_block`, so a defect with no attempt at all gets none.
   Worth a test either way; I have not written it.
3. **`model-sees-no-edit-or-test-result`** — **the best finding in the run, and it
   is about the fix I just made.** The new failure-detail field records pytest
   failure text and carries it through `SetAsideTest`, and the review points out
   that a later prompt could expose edit-derived test results. I believe there is
   no present violation: `SetAsideTest.detail` comes from the baseline run against
   the code as delivered, before anything is injected, and
   `tests/test_unverified_mutation_is_inert.py::…::test_the_static_judge_is_told_nothing_about_the_edit`
   still passes. But `TestOutcome.detail` *is* populated for mutant runs, so the
   hazard is real and one commit away. It needs a test that pins the boundary
   rather than an argument that it holds today.

## The unrequested-change detection caught the separable commit

I predicted it would flag `07d61a8` as `separable` and it did not; it flagged it
as **`in_service`**, naming the `detail` field precisely and saying the
obligations do not require it. It also flagged the `judge_pairs` signature change.
So detection worked and the disposition is the arguable part — an addition made
for a different purpose reads to me as separable rather than in service of the
mandate. Not queued: one disagreement about one disposition is not evidence, and
#301, the filed defect where a scope exclusion gets one of three different
dispositions, already covers disposition instability.

## The measurement, unchanged

1,885 of 20,295 pairs dropped — a **9.3% saving**, against 9.8% in run 1. 13
killed attempts, of which 7 dropped anything; the other 6 had their held-back
pairs judged after all, which is rule 6 working.
