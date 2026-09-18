# Judgement — #45 Gate 2, run 3

**Not clean.** Verdict INCOMPLETE. Run `34e2dd05d2fd3f0b`, continuing run 2's
`87896b868ce088e4`. Base `61c5a3c`, head `82b29b5`. **$11.5874 over 1394 live
calls**, against $5.12 in run 1 and $3.78 in run 2.

Five of 33 criteria came back with test evidence that only partially
discriminates, and 21 unrequested changes were detected. No open questions.

## The decision not to run the tests worked, end to end

The report carries it:

> the project's tests were not run: no result could have counted. Edit
> verification is off, so every observation would have been recorded as not
> counted, and nothing else consumes the run. See #335 for the check that would
> make injection earn its evidence.

That is ruling 3 working in the real report, and it is the honest position #45
lands in: the execution tier is wired, tested and dormant.

## Why this run cost more than either before it

Nothing carried forward. The `--continue` carry matches on obligation text, and
the mandate was substantially rewritten to apply the three rulings, so all 33
criteria were re-decomposed and every pair re-judged: 1330 pair-judgement calls
at $10.09 of the $11.59.

**And execution settled nothing, so every pair went to the static judge.** That
is the cost of the tier earning nothing, stated in one number: the stage this
milestone exists to replace was paid in full.

## The five weak criteria, triaged

| criterion | disposition |
|---|---|
| `run-candidate-tests-on-throwaway-copy` | **genuine gap — fixed** |
| `one-failing-test-covers-defect` | **my mandate wording was wrong — fixed** |
| `run-tests-when-result-will-be-used` | **genuine gap — fixed** |
| `pre-alteration-single-run` | **genuine gap — fixed** |
| `test-discrimination-shown` | **tool defect (mapping) — queued** |

**The collection gate had no test at all.** I verified that nothing in `tests/`
referenced `collect_tests`. That function is the fix for the failure that left
the execution tier completely inert in run 2 — one archetype-fixture test that
pytest refused took all 341 candidate tests down with it. A helper the pipeline
depends on with nothing exercising it is exactly the shape CLAUDE.md warns
about, and the tool found it. `tests/test_execution_collection_gate.py` now
covers it, including the case the recommendation named.

**The coverage sentence I wrote applying ruling 1 was too strong.** It said a
defect any test fails on is covered, full stop. The recommendation pointed out
that a failing test whose failure is a missing name, or one of a great many
failures, is discarded rather than counted — the two checks approved on
2026-09-17. So the sentence as written contradicted them. Reworded: one failing
test is enough, for a failure the edit caused. The ruling is unchanged; my
rendering of it was wrong, and the tool caught it.

**Two more genuine gaps, both fixed.** `decide_execution` had no direct test, so
`tests/test_execution_decision.py` now covers every branch and that each
carries a reason. And the control run preceding any descriptor was proved only
indirectly; `TestTheControlRunComesFirst` now asserts the call order and that it
runs once rather than per defect.

**One tool defect.** For `test-discrimination-shown` the recommendation asks for
an observed-but-unverified attempt rendered against a verified control. That
test exists — `test_the_report_says_the_result_is_not_counted` and
`test_a_verified_result_carries_no_such_mark` — and the pair judgement linked
both to two *other* criteria instead. A prescription for evidence the review
already holds is #250 and #287's failure shape. Queued as a filing against #183,
the evidence-judgement umbrella.

## The 21 unrequested changes

Nearly all are one shape: "this adds a public module or exported API the
obligations do not ask for". That is true of every new module in a feature this
size, and the mandate describes behaviour rather than an API surface. Not acted
on.

The two marked risky both turn out to be in service of work the human approved:

- `run_check` gaining an `execution` parameter is how the settings reach the
  pipeline, which ruling 3 requires.
- `error_type` recording in `netblock.py` is the missing-name check approved on
  2026-09-17.

One marked separable is `src/acceptance/mutation/__init__.py`, a package docstring.

## Not re-run

The fixes re-arm the gate and a fourth run is owed. It costs about $11.59 and
re-decomposes the mandate again, because the wording changed. That is a spend
decision for the human, and the merge is theirs regardless.

1633 passed, 1 skipped, 2 xfailed. `ruff check` and `ruff format` clean.
