# Judgement — #269 Gate 2, run 5

`check --task current-task.md --base a4abbf4 --head 87b8754`. The only difference
from run 4 is `87b8754`, which **adds nine tests and changes no source file.**

**Not clean, and dramatically worse.** `Task completion: INCOMPLETE` — **48 of 60
obligations** less than strongly supported.

| rating | run 4 | run 5 |
|---|---|---|
| strongly supported | **37** | **4** |
| partially supported | 3 | 48 |
| nominally supported | 8 | 0 |
| unsupported | 4 | 0 |
| not required | 8 | 8 |

**Adding tests made 33 obligations worse.** That is not a possible consequence of
the change: no source file moved, no obligation text moved, and every test cited
in run 4 still exists and still passes (1215 passing).

## The clean instance

Obligation 1, `unchanged-task-file-no-decompose-call`, is the sharpest case
because run 5 cites a **superset** of run 4's evidence:

| | run 4 | run 5 |
|---|---|---|
| rating | **strongly supported** | **partially supported** |
| cites | `test_a_rerun_over_an_unchanged_task_file_issues_no_decompose_call`, `test_the_plan_issues_calls_only_for_what_changed` | the same first test, plus `test_the_alignment_helper_is_not_called_when_nothing_is_left_over` and `test_the_decompose_command_writes_a_ledger_entry_and_a_second_run_carries` |

Same on-point test, one more mapped test, weaker rating. There is no reading of
"the evidence got worse" that survives that.

The report's own delta section says it plainly — `Changes since 2276c135:` lists
line after line of `test evidence: strongly supported -> partially supported`.

## What this is

The defect queued from run 3 — *a rating dropped from strongly supported to weak
on unchanged evidence* — at a scale that removes any doubt about it. Run 3's
instance was two obligations and could be argued as noise. This is 33, in one
direction, caused by adding evidence.

Run 5 is an incremental re-run: `find_prior_review` selected run 4's stored review
and re-judged the obligations the change could have affected. Nearly every
obligation cites `tests/requirement/test_carry_forward.py`, so nearly every
obligation was re-judged — and nearly every re-judgement came back a tier lower.
Whether the mechanism is the re-judgement path or the strength judge itself is
the open question the filing has to answer; the observable fact is that the
second look is systematically harsher than the first on strictly more evidence.

This also puts a hard limit on what any Gate 2 rating in this repository is worth
right now: a rating is a function of how many times the obligation has been
looked at, not only of the evidence under it.

## Disposition

**Tool defect.** Filed against **#183** (evidence judgement), strengthened from
run 3's draft with this run's numbers, and cross-referencing **#251** — *a
criterion is re-judged only when its own inputs changed, and a changed rating
names the change* — which is very close to being the fix.

**Stopping here.** Chasing a clean Gate 2 against a judge that degrades as
evidence improves would mean writing tests to satisfy a rating that moves for
reasons unrelated to them. #269's own work is not implicated: 1215 tests pass,
the nine gaps run 4 named are closed, and the last trustworthy reading of the
obligation set is run 4's.

## What is still genuinely open on #269

One item, unchanged from run 4 and honest: `completion-10` asks that the
movements recorded in `tests/fixtures/decompose-stability/` still be produced,
and no test runs carry-forward over that corpus. That is real work, not a rating
artefact.
