# Judgement — #293 Gate 2, run 1

```bash
.venv/bin/acceptance check --task current-task.md --base 55ff7ee --head c7141b8 \
  --mode record --continue a84c1b0c6e71916a
```

Run `6f64baa7e8cf3a78`, continuing Gate 1 run 2. `output.log` is 30,728 bytes.
Exit 0. $0.1500 on 11 live calls; decomposition and obligation linking replayed
from the continued run, so the obligation set is Gate 1's and not re-derived.

Base `55ff7ee` is the Gate 1 commit — after the mandate and its rewords, before
any implementation — so the diff under review is the delivery and nothing else.

## The gate is NOT clean. One blocker.

**Task completion: INCOMPLETE.** Everything else passes:

| axis | count |
|---|---|
| obligations, all `code evidence: addressed` | 22 |
| `test evidence: strongly supported` | 13 |
| `test evidence: not required` (scope exclusions and absence-satisfied) | 8 |
| **`test evidence: unsupported`** | **1** |

No open questions (the dead axis, #303). Seven unrequested changes, **all seven
dispositioned `in_service`** — advisory, none `separable` or `risky`.

## The blocker: obligation 17 has no mapped test, and the test exists

Obligation 17 is `adding-test-to-unmapped-file-leaves-rating-unchanged`
(`completion-03`): *"Adding a test to a file that already holds a mapped test
leaves unchanged the rating of a criterion whose own mapped tests were not
edited."* The report gives it `code evidence: addressed`, then
`test evidence: unsupported — (no mapped test)`, and prescribes:

> After adding a test to a file that already contains a mapped test, a criterion
> whose mapped tests were not edited keeps the same rating. […] a fresh run where
> that mapped test's source is byte-identical but an additional, unrelated test is
> appended to the same test file.

That is `tests/evidence/test_rejudge.py::test_a_test_appended_to_the_same_file_does_not_disturb_the_rating`,
which is in the diff under review, and which the report itself cites twice — as
evidence 1.16 and 2.15, under two *other* obligations. The tool is asking for a
test it can see.

## It is a mapping judgement defect, not a partitioning one

The two are worth separating, because `DR-164` makes partitioning the usual
suspect and it is not the cause here.

Transcript `.acceptance/cache/transcripts/c3f75a2e067ea3d7f5c1f190ec5c6b8d4035119f161e418f8e34b58bdf0a1102.json`
contains **both** the obligation and the test in one request. The mapper answered
12 mappings. For the test in question it returned:

```
['compare-by-test-contents-not-file-touch',
 'unchanged-inputs-keep-stored-rating',
 'criterion-test-evidence-re-derived-only-when-own-inputs-changed',
 'criterion-inputs-are-requirement-text-mapped-test-set-and-test-contents']
```

Four obligations, none of them obligation 17 — and **no test at all** was mapped
to obligation 17 in that call. So the pair was shown together and declined, while
four looser matches were accepted. Mapping was not half-blind overall: obligations
1 and 2 carry 20+ mapped tests each.

**A hypothesis worth recording, not a conclusion.** The mapper is shown each
obligation's id, description and observable behaviour. This obligation's id says
`adding-test-to-**unmapped**-file-…`, which asserts the opposite of its own
description — the file in question is precisely one that *does* hold a mapped
test. That contradiction was noticed at Gate 1 run 1 and recorded as cosmetic. It
may not be. It is untested either way, and the fix is not mine to guess at.

## Disposition

**Attributed to a tool defect, and queued as a filing under #182** (test discovery
and mapping). There is no honest code change available: the test exists, is
correct, and is defect-injected. Writing a second test to coax the mapper would be
rewriting the output rather than the software, which the gate rules forbid.

**This is a stop.** Under the working agreement the gate is not clean and I do not
open a PR. #291 and #292 both merged with Gate 2 deliberately not clean on the
human's written approval; the same call is asked for here rather than assumed.

## The acceptance items, and how each is demonstrated

Named tests, not intent. All pass; the full suite is 1486 passed, `ruff` 0.16.2
clean.

| Acceptance item | Demonstrated by |
|---|---|
| Unchanged text + mapped set + mapped contents keeps the rating | `test_a_criterion_with_all_three_inputs_unchanged_keeps_its_stored_rating` |
| …and costs no evidence-judgement request | `test_the_pipeline_carries_the_rating_and_leaves_the_criterion_out_of_the_request` |
| Compared by test contents, not by whether a file was touched | `test_a_test_appended_to_the_same_file_does_not_disturb_the_rating`, `test_the_stored_digests_are_per_test_and_not_per_file` |
| Appending a test to a mapped file leaves the rating alone | same, plus the pipeline test above |
| Editing one criterion's test leaves others alone | `test_editing_one_criterions_test_leaves_another_criterion_alone` |
| A gained or lost mapped test is judged again | `test_a_gained_mapped_test_forces_a_re_judgement`, `test_a_lost_mapped_test_forces_a_re_judgement` |
| Changed requirement text is judged again | `test_a_reworded_requirement_forces_a_re_judgement` |
| The file-touch rule is retired | `stale_obligation_ids` and `obligations_to_rederive` deleted; `test_a_moved_obligation_set_forbids_reuse` covers the one rule that remains |
| The two staleness axes are decided separately | `test_a_stale_prior_verdict_is_replaced_rather_than_surviving` (coverage always re-derived) alongside the carry tests |
| Byte-identical review state over the same inputs | `test_two_runs_over_the_same_inputs_compute_the_same_key`, plus the existing determinism suite |
| The `rating-stability` fixtures are still found | `tests/benchmark/test_rating_regression.py`, unchanged and passing |

## Defect injection

Both new test groups were checked against a deliberately broken build rather than
assumed to bite.

1. **Digest the whole file rather than the test** — the exact defect #293 removes.
   Three tests failed, including the pipeline wiring test:
   `test_a_test_appended_to_the_same_file_does_not_disturb_the_rating`,
   `test_editing_one_criterions_test_leaves_another_criterion_alone`,
   `test_the_pipeline_carries_the_rating_and_leaves_the_criterion_out_of_the_request`.
2. **Compute the carry decision and then ignore it** (`to_judge = list(needs_tests)`)
   — the "helper the pipeline never calls" hole this repo keeps finding. Exactly
   the wiring test failed, and the unit tests all still passed, which is the point
   of having it.

Reverted with `git checkout --` after each.
