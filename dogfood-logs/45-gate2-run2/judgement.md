# Judgement — #45 Gate 2, run 2 (with `--execute`)

Run `87896b868ce088e4`, continuing run 1's `4e93f560eb546ef5`. Base `61c5a3c`,
head `518f876`. $3.7759 over 528 live calls. Verdict INCOMPLETE.

**The execution tier ran and settled nothing.** All 71 defects came back
`not_attempted`, every one with the same reason: *"no candidate test survived
the control run, so there is nothing a mutant could be observed against"*.

## Why the control run produced nothing

The sandboxed pytest exited with code 4 and wrote no report, so all 341
candidate tests were recorded `not_started`.

I reproduced it outside the review. Passing the 341 discovered node ids to
pytest fails collection with:

```
import file mismatch:
imported module 'test_report' has this __file__ attribute:
  tests/fixtures/archetypes/08-unrequested-change-separable/head/test_report.py
which is not the same as the test file we want to collect:
  tests/test_report.py
```

348 tests collect, one file errors, and the error takes the whole run to exit 4.
The cause is a **module basename collision** between a real test file and an
archetype fixture that shares its name, in a tree with no `__init__.py` files.

I verified the sandbox itself is sound: the identical invocation over a single
real node id exits 0 and writes its report correctly. The failure is this
repository's test layout, not the sandbox.

This is plausibly the same root cause as the open question `CLAUDE.md` records —
why a local `pytest` run collects ten fewer tests than CI does on the same
commit — and that investigation is one of the two exempted from the gates.

## A defect this run found in my own wiring

**71 descriptor calls were bought and thrown away, for $0.2554.**
`_run_execution_tier` built every descriptor *before* `run_mutations` checked
whether any test was usable. The check exists and is correct; it just ran too
late to save anything.

`test_no_mutant_is_built_so_no_descriptor_is_asked_for` passed throughout,
because the runner genuinely does not ask for descriptors — the pipeline does.
That is exactly the shape `CLAUDE.md` warns about, a helper with a good test
that the pipeline uses differently, and my own test gave false comfort.

Fixed: the pipeline returns as soon as the baseline offers no usable test, and
two wiring tests now assert no descriptor call is made and that the defects
still reach the static judge.

## The cost, and what the saving actually was

| | run 1 (static only) | run 2 (`--execute`) |
|---|---|---|
| total | $5.1153, 686 calls | $3.7759, 528 calls |
| pair judgement | $4.5830, 658 calls | $3.1478, 439 calls |
| defect enumeration | $0.4133, 25 calls | $0.2541, 15 calls |
| mutation descriptor | — | $0.2554, 71 calls |

**The $1.34 difference is the `--continue` carry, not injection.** Injection
settled zero defects, so `judge_pairs` received all 71 and the saving came
entirely from pair verdicts reused by identity from run 1's ledger. Injection's
only effect on this run was to add $0.2554 of wasted descriptor calls.

So this run measures nothing about the milestone's premise. The measurement is
still owed, and it needs the collection collision fixed first.

The pair stage reported **0.7% cached**, against 0.0% in run 1 — still
effectively nothing, and still evidence for #324.

## Wall clock

Far less than the hour I estimated, because no injection ran. The estimate
stands untested.

## Findings, down from seven to four

`test-fails-discriminate-defect`, `candidate-tests-run-once-before-changes`,
`report-lists-set-aside-tests`, `mechanical-validity-checks`. Three of run 1's
seven closed against the fixes made after it. The recurrence of
`report-lists-set-aside-tests` and `mechanical-validity-checks` is worth reading
carefully at the next round rather than assuming the fixes missed.
