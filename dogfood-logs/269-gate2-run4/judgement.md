# Judgement — #269 Gate 2, run 4 (first run after #279)

`check --task current-task.md --base a4abbf4 --head 87b8754^`, branch rebased
onto `origin/main` at `a4abbf4`.

**The review renders again.** #279 (*record an omitted recommendation instead of
abandoning the review*) fixed the abort that blocked run 3, and the whole report
is available for the first time since run 2.

**Not clean.** `Task completion: INCOMPLETE` — 15 obligations less than strongly
supported: 4 unsupported, 3 partially supported, 8 nominally supported.

## The gaps, and which were mine

Nine were genuine holes in my tests, and all nine are now closed (`87b8754`):

| obligation | what was missing |
|---|---|
| `constraint-23` — run id in no rendered report | I asserted it against review state, never against what the CLI prints |
| `constraint-30` — ledger records the call count | asserted incidentally inside a test about something else, never on its own |
| `constraint-08` / `task-01` — a new requirement derives fresh | no test at all for the new-requirement path |
| `constraint-10` — the residue goes through `align_obligations` | never asserted the aligner is invoked |
| `constraint-13` — reads only the named run | no decoy entry, so nothing distinguished "read the named run" from "read whatever was there" |
| `constraint-20` / `task-02` — every run reports an identifier | never asserted the CLI prints one |
| `constraint-25` — append-only | the test asserted the refusal but not that the file survived it |
| `constraint-09` — exact text defines identity | only exercised implicitly, and never with an insertion, which is the case that separates textual identity from positional |

Two of the recommendations were better than what I would have written unprompted.
`constraint-13`'s named the decoy: without a second ledger entry present, the test
passes on an implementation that ignores the run id entirely. `constraint-10`'s
said to instrument the client, because the outcome alone cannot distinguish *the
aligner matched them* from *the planner guessed by position* — and position is
exactly what identity must not be.

Writing them found a flaw in an existing test of mine: reusing one client across
two `run_decompose` calls replays the second from the transcript store, so a call
count cannot tell a carried run from a replayed one. That test now asserts on the
ledger.

## Where the finding was weaker than the report implies

Several of the eight `nominally supported` obligations cite tests that have
nothing to do with them — `constraint-03` (obligation descriptions carried
unchanged) cites `test_obligation_echo.py::test_a_remainder_differing_in_any_single_field_is_kept`,
and three `task-02` obligations all cite
`tests/test_cli.py::test_check_persists_the_review_to_the_store`. Meanwhile
`test_a_rerun_over_an_unchanged_task_file_returns_byte_identical_obligations`,
which asserts descriptions explicitly, is not cited against `constraint-03`.

That is mapping noise rather than an evidence gap, and it is the #182 axis. Not
filed separately — the tests were written anyway, and a mapping miss that
prompts a real test is a cheap failure.

## `completion-10` is the one I could not close honestly

*The decomposition movements recorded as correct in
`tests/fixtures/decompose-stability/` are still produced when the task file
genuinely changes.* The obligation names the corpus, and my anti-blunting test
(`test_carrying_forward_does_not_freeze_a_superseded_obligation_in_place`) asserts
the property generically without touching the corpus. #195's regression suite
uses the corpus but does not exercise carry-forward.

So the mapper is right that no test covers what this obligation literally asks
for. Closing it properly means running carry-forward over the corpus, which is a
piece of work in its own right. Left open deliberately rather than papered over.

## Disposition

No tool defect attributed from this run. Nine tests added; see run 5 for what
happened next.
