# Judgement — #266 Gate 2, run 1

`check --task current-task.md --base 265bfac --head 28f2e2d`, recorded then
replayed byte-identically.

## NOT CLEAN

**Verdict `INCOMPLETE`. 9 of 30 obligations rated `unsupported` with `(no mapped
test)`, each carrying a recommended test.** No open questions, nothing flagged
for human review, one advisory unrequested change correctly dispositioned
`in_service`.

| | count |
|---|---|
| strongly supported | 15 |
| unsupported, with a recommendation | 9 |
| not applicable (scope exclusions, code-only) | 6 |

Every obligation is `addressed` on the coverage axis. The gap is entirely on the
test-evidence axis.

## All 9 are one known mapping defect — #245

Every one of the nine has an on-point test **that the mapping stage saw and
mapped to the twin obligation instead**. Read off the recorded `_Mappings`
transcripts (118 candidate tests offered, 17 of them this change's own):

| unsupported obligation | the test that evidences it | what the stage mapped that test to |
|---|---|---|
| `test-review-does-not-abort-on-no-test-can-evidence-statement` (completion-02) | `test_a_declined_obligation_does_not_abort_the_review` | `recommendation-may-state-no-test-can-evidence-criterion` (constraint-01) |
| `test-omitted-criterion-still-aborts-review` (completion-03) | `test_an_omitted_obligation_still_aborts_even_when_others_are_declined` | `missing-recommendation-or-statement-aborts-review` (constraint-04) |
| `test-statement-attributed-to-criterion-in-persisted-state` (completion-04) | `test_the_refusal_reaches_review_state_attributed_to_its_obligation` | constraint-05, constraint-06 |
| `test-all-weak-criteria-answered-that-way-produce-report` (completion-05) | `test_a_config_only_change_produces_a_report` | `config-only-change-produces-report`, task-01 |
| `test-report-omits-no-test-can-evidence-statement-for-no-recommendation` (completion-08) | `test_the_report_says_no_such_thing_for_an_obligation_that_merely_lacks_one` | `report-omits-no-test-statement-for-no-recommendation` (constraint-10) |
| `no-test-evidence-statement-carries-reason` (constraint-02) | `test_a_declined_obligation_does_not_abort_the_review` (asserts `.reason`) | constraint-01 only |
| `no-test-evidence-statement-does-not-abort-review` (constraint-03) | same test | constraint-01 only |
| `weak-criteria-all-statement-produces-report` (constraint-07) | `test_a_review_of_only_declined_obligations_is_unable_to_determine` | task-01 only |
| `addressed-criterion-indeterminate-on-test-evidence-axis` (constraint-08) | `test_a_declined_obligation_is_indeterminate_on_the_evidence_axis` | `test-addressed-criterion-classified-indeterminate-on-test-evidence-axis` (**completion-06**) |

The shape is systematic: a Constraint and the Completion expectation that demands
its test are a twin pair, and the stage assigns the on-point test to **exactly
one of the pair**, leaving the other with nothing. That is #245 —
*"Mapping splits a Completion expectation from its Constraint twin, unstably"* —
and the last row is the mirror image, mapping to the completion twin and starving
the constraint, which #245's title does not currently cover.

Attributed to the tool, with a comment queued on #245. **Not a test that is
missing**: each named test exists, runs, and was shown to the judge.

## The aggregate emptiness figure is a red herring — recorded so nobody re-derives it

93 of 118 mapping entries came back with empty `obligation_ids` (79%), which
looks like DR-164's shed-work signature. **It is not.** A mapping entry is per
*candidate test*, and this repo has ~1,100 tests of which almost none bear on
this mandate, so an empty answer for an unrelated test is the correct answer.
The diagnosis had to come from the 17 relevant tests specifically, not the ratio.

## Three of this change's own tests mapped to nothing, correctly

`test_a_duplicate_refusal_is_rejected`,
`test_a_refusal_naming_an_obligation_the_call_did_not_supply_is_rejected` and
`test_an_obligation_both_recommended_for_and_declined_is_rejected` got empty
answers. No obligation demands them — they guard invariants I added beyond the
mandate. Correct, not a miss.

One real miss beyond the nine: `test_a_declined_obligation_is_an_escalation_candidate`
mapped to nothing, though it bears on constraint-08.

## The stop reason is already paying for itself

Every `_Mappings` call in this run recorded `stop_reason: stop`. Ruling out
truncation as the cause of the empty answers took one field lookup, where #266's
own diagnosis needed token counts and JSON well-formedness reconstructed by hand.
That is constraint-13 doing exactly the job it was added for, on its first run.

## Not a blocker

**Unrequested change, `in_service`:** the `RecommendationOutcome` return wrapper.
The disposition is right — the stage has to return two lists now, and the caller
has to unpack them. Advisory, correctly not counted against the verdict.

## Disposition

**Gate 2 fails. No PR.** The nine findings are attributed to #245 with the
evidence above and a queued comment; the gate stays armed. What is not yet
established is whether a re-run moves them — #245 records the split as
*unstable*, so a second `check` may well produce a different nine, and that
movement is itself the finding. Costs another record run.
