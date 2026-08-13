# Judgement — #266 Gate 2, run 2

`check --task current-task.md --base 265bfac --head b55eef5`. First run after
the mapping-prompt fix.

## NOT CLEAN — but the mapping fix worked

Verdict `INCOMPLETE`, **2 of 34 obligations short of strongly supported**, down
from 9 of 30 in run 1.

The task file grew by two constraints and two completion expectations covering
the mapping change itself, so the denominator moved; the numerator is what
matters. Seven of run 1's nine went green with no test added and no test
changed — only the instruction to the mapper changed. That is as direct a
confirmation as this setup can produce that they were mapping failures, not
evidence gaps.

## The two that remain are the two predicted

Before run 2 was taken, run 1's judgement had split the nine into "solid #245
attribution" and "mine to fix". The residual is exactly the second group.

### `no-test-evidence-statement-carries-reason` (constraint-02) — real, and now fixed

Rated `nominally supported` — a mapped test with no discriminating power, not an
absence. The recommendation asked for a case where the reason **is omitted or
empty**.

That was a genuine hole and the recommendation found it: `reason` was a required
field, and `""` is a valid `str`. A response could satisfy every structural
check and still withhold the judgement — which is precisely the unauditable
silence this whole change exists to reject, reintroduced one level down.

Fixed rather than attributed: `recommend_tests` now rejects a refusal whose
reason is empty or whitespace, with a test over `""`, `"   "` and `"\n"`, and a
control asserting a real reason is still accepted.

### `test-review-produces-report-when-all-weak-criteria-have-statements` (completion-05) — real, and now fixed

Rated `unsupported`. Its constraint twin (constraint-07) is `strongly
supported`, so this is the last surviving twin split — but the recommendation
was right on the merits anyway: there was no test whose *subject* was the
all-refusals case. It was a passenger in `test_a_config_only_change_produces_a_report`,
an end-to-end test about configuration-only changes.

Fixed with a stage-level test asserting the all-declined case at the boundary
where the abort used to occur, carrying the contrast that makes it evidence:
the same obligations with one refusal removed must still raise.

## What this run settles about run 1

Run 1's judgement attributed all nine findings to #245. That was two-thirds
right and one-third too convenient — a point the human made before this run was
taken, and the run confirms it. Both residual findings were real defects in this
change, and one of them (the empty reason) was a genuine weakness in the
delivered code, not a test-shape complaint.

Recorded because the failure mode is worth remembering: attributing a finding to
a known tool defect is cheap, plausible, and indistinguishable from suppressing
it until something forces the split. Here the forcing function was fixing the
tool defect and re-running.

## Disposition

**Gate 2 fails, and the gate is now legitimately re-armed** — two corrections
were made in response to these findings, so run 3 is owed and is a real re-run
rather than a re-roll.
