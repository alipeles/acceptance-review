# Judgement — #244 Gate 2, runs 1 and 2

**Gate 2 is not clean.** Verdict INCOMPLETE in both runs, two obligations below
strongly supported each time. Neither remaining finding is an unmet requirement,
and iterating further is not a terminating procedure — see below.

Run 1 head `3471623`; run 2 head `dd4caf5`, differing by one added test written
in response to run 1's first finding. Base `75fefc4` for both.

| | run 1 | run 2 |
|---|---|---|
| verdict | INCOMPLETE | INCOMPLETE |
| `test-obligation-keeps-own-span` | partially supported | partially supported |
| `tests-issue-no-live-model-calls` | **nominally supported** (2 mapped tests) | **unsupported** (no mapped test) |
| recommended tests | 2 | 2 |

## Finding 1 — the recommendation now asks for the test it is already citing

Run 1 rated `test-obligation-keeps-own-span` partially supported and recommended:

> Construct a task file with at least two requirements whose text overlaps enough
> that one obligation's quotation appears inside both spans, but attribute that
> obligation to the requirement whose own span already contains the quotation.

That was a **real and good finding**. The existing tests used non-overlapping
requirement text, so they could not catch an implementation that ignored the
attributed-first preference — which is the load-bearing part of the fix. I wrote
`test_a_quotation_matching_two_requirements_stays_with_the_one_it_was_attributed_to`
and confirmed by defect injection that it fails when that branch is disabled.

Run 2 maps that new test to the obligation (cited as `1.2`), keeps the rating at
partially supported, and recommends:

> Use two requirements whose text both contain the same quoted phrase, but
> attribute the obligation to the later requirement.

Which is a description of the test it just cited. The `detects:` clause names a
defect — "only checks the attributed requirement first and never searches other
requirements" — that `test_an_obligation_quoting_another_requirement_is_refiled_under_it`
catches, mapped to the neighbouring obligation.

Disposition: **tool defect, evidence judgement (#183)**. Queued as a filing.
Addressing it further would mean writing a third test of the same property to
satisfy a recommendation that already cites the second.

## Finding 2 — the mapped set collapsed from two to zero

`tests-issue-no-live-model-calls` was **nominally supported** in run 1 with two
mapped tests, and **unsupported, no mapped test** in run 2. The only change
between the runs is a test added to a different obligation's area. Nothing about
this obligation, its requirement text, or the tests that evidence it changed.

Both runs also miss the three tests that directly evidence the property:
`tests/test_determinism.py::test_replay_reproduces_a_recorded_run_with_no_live_call`,
`tests/test_llm.py::test_recorded_transcript_replays_with_zero_live_calls`, and
`tests/test_llm.py::test_replay_without_a_transcript_raises_rather_than_calling_live`.

Disposition: **tool defect, mapping (#182)**. Queued as a filing.

**This independently reproduces the #214 lane's finding** on the same obligation
text (`issuecomment-5245416368`): their run 1 had it strongly supported citing
two mapped tests, their run 2 unsupported with none. Two lanes, different
changes, the same obligation, the same collapse from two mapped tests to zero.

## Unrequested changes — one is fair

Five reported, four `in_service` and correctly so: they are the implementation of
the mandate. The fifth is `separable` and is a fair call:

> Documentation edits in CLAUDE.md and docs/DEFERRED.md are unrelated to the
> obligation-attribution task.

Correct. The CLAUDE.md wording fix was approved separately and the queue entries
are process records; both rode along in #244's first commit rather than standing
on their own. Noted rather than acted on, since splitting them now would rewrite
a commit already used as a dogfood revision.

## Why iterating stopped here

The Gate 2 procedure says to fix what the check reports and re-run until clean.
Run 1 → run 2 shows that is not converging: the one finding I addressed produced
a recommendation for the test that addressed it, and an untouched obligation lost
its entire mapped set. That is #180's non-convergence, met inside #244's own
gate, and it is why #153, #235 and #214 each merged on an explicit human call.
