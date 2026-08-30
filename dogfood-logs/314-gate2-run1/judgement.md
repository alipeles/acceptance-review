# Judgement — #314 Gate 2, run 1

**The check is not clean.** It reports INCOMPLETE: 3 criteria not fully
implemented and 4 with test evidence rated unsupported. Run once and not
iterated, per CLAUDE.md's suspension of the clean-or-stop rule while #312's
sub-issues land. No open questions, no unusable answers, and nothing flagged as
needing non-code evidence or human review.

Base `5554c79`, head `2945551`, run `fc5fdcb24820a37e`, continuing
`e48c34926a8370e2`.

## Real findings, acted on

**`request-shape-choice-excluded` — not addressed. The tool is right, and this
is my wording.** My Scope exclusion said the change "does not include choosing
between candidate shapes for the request that carries the pair question", and
the branch then committed `docs/DR-314-pair-response-shape.md` and
`docs/experiments/pair-response-shape/`, which are exactly that choosing. The
exclusion was meant to say the *software* does not pick a shape at run time; as
written it said the *change* contains no such decision, which is false. Fixed
the wording in `current-task.md`. The finding stands as correct.

**`pair-question-matches-failure-test` — unsupported, no mapped test. A genuine
gap.** Nothing asserted that the request actually poses the failure question.
Every other test drives a double that ignores the prompt, so the whole suite
would have passed against a stage that asked the retired relevance question
instead — which is the one thing #312 exists to replace. Closed with
`test_the_question_put_about_a_pair_is_the_failure_question`.

**`judged-pair-response-minimality` — unsupported, no mapped test. A genuine
gap.** Nothing asserted the response carries only the pair, the verdict and a
short reason. Closed with
`test_the_answer_about_a_pair_carries_only_the_pair_the_verdict_and_a_reason`,
which reads the schema as sent rather than the model class, since the sent
schema is what bounds the answer.

## Attributed to known tool defects — noted, not re-filed

Per the suspension: a finding that is only evidence of an already-known defect
needs nothing beyond a line.

**Two mapping misses on twin criteria.** `test-covers-unsettled-path-pair-judgment`
and `verdict-not-reproduced-when-unchanged` are both rated unsupported with "no
mapped test", and both are covered.
`tests/defects/test_reachability.py::test_judges_when_the_defect_implicates_no_file`
asserts the first; `test_a_verdict_is_reused_when_its_defect_and_its_test_are_both_unchanged`
asserts the second. In both cases the test was mapped to the Constraint twin and
not to the Completion expectation stating the same demand — #245, mapping splits
a Completion expectation from its Constraint twin, and #304, twin obligations
left unmerged.

**A preservation criterion rated not addressed.**
`completion-report-complete-ratings-tests-as-if-no-pair-judged` — that the
review's verdict, ratings and recommendations are what they would be with no
pair judged — is rated `not addressed` on the code axis while its test evidence
is strongly supported by `test_judging_pairs_changes_no_verdict_rating_or_recommendation`,
a difference test that fails if the property breaks. A diff cannot exhibit an
invariance, which is #213: a preservation obligation is unsupported even when a
passing regression suite is its evidence.

**A scope exclusion rated partially addressed.**
`no-change-to-test-evidence-workflow` is `partially addressed`, citing
`pipeline.py`, `report.py`, `review_state.py` and the new stage. I verified the
change touches none of `evidence/mapping.py`, `discrimination.py`,
`strength.py` or `classification.py`; it inserts a call into `pipeline.py`
before them and adds a report block after them. #301, where a scope exclusion
receives one of three different dispositions.

## The measured cost, which #314 asked for

The pair stage issued **332 calls** on this review, costing **$3.51 of the run's
$4.25** — 1,398,868 prompt tokens and **546,143 output tokens**, against the
whole rest of the pipeline's 43 calls and $0.74. Two things drive it: one
request per test, and a verdict per offered defect. Both were deliberate and
both are recorded with their reasons in `DR-314-pair-response-shape.md` and
`defects/pair_mapping.py`. Output tokens do not amortize, so this is the figure
#316 should watch, and it is the figure that would justify funding real
reachability as its own issue.

## What the shadow comparison showed on its own delivery

The new report block ran over this review and named 8 criteria where the support
implied by pairs is lower than the rating the review gives. Every disagreement
is in that direction — the pair join is more conservative than the current
chain, never more generous. Example: `test-failure-matrix-recording` is rated
`strongly_supported` today and the pairs imply `partially_supported`, killing 1
of 4 enumerated defects. That is the comparison doing exactly the job DR-312
decision 5 wanted it to do before #316 flips the source, and it is data the
cutover decision should see.

## Unrequested changes

Four, all dispositioned `in_service`: wiring the stage into the pipeline and
ledger, the report block, the prefilter, and the ledger-entry field plus the
sink tuple shape. All are in service of the mandate and none is separable.
