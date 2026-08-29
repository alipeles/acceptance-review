# #313 Gate 1, run 5 — judgement

**Gate 1 passes on this run.** No obligation states the opposite of its
requirement, no obligation is invented, no requirement is unaccounted for, and no
open question was raised.

Command: `.venv/bin/acceptance decompose --task current-task.md --continue 2b8741189def35cc`
Run id: `3d391de59262b762`. 29 requirements, 28 with obligations, 1 deliberate
none. 0 derived, 27 carried, 2 revised, 2 decompose calls.

## Stating the requirement positively fixes the polarity inversion

Runs 3 and 4 both derived obligations demanding the behaviour their requirement
forbids, on two different wordings of the "A test fails when X" form. Run 5
drops that form for the two affected requirements and states the demanded
behaviour directly. Both came out correct on the first try.

| requirement | run 4 (form: "A test fails when X") | run 5 (form: "A test asserts that Y") |
|---|---|---|
| `completion-02` | "A test asserts that the step … **can see any test**" — inverted | "A test asserts that the step … **is given no test**" — correct |
| `completion-06` | "A test asserts that a criterion whose text is unchanged **has its set produced again** …" — inverted | "A test asserts that changing one criterion's text **leaves every other criterion's set reused** …" — correct |

Both were among the 2 revised and so were re-derived, not carried. This is a
workaround, not a fix: the derivation still cannot be trusted to invert "a test
fails when X" reliably — 5 of 7 in run 3, the same 5 of 7 in run 4 — and
`completion-03`, `-04`, `-05` and `-07` still use the form and still happen to
come out right. The finding stands and is recorded against #262, the issue for a
paraphrase that does not preserve entailment.

Worth keeping for whoever writes the next task file: **a completion expectation
that states what a test must assert derives correctly; one that states when a
test must fail requires the model to invert, and it inverts unreliably.**

## The `unknown` stage row is gone, verified in a real run

Run 4's footer carried a row headed `unknown`. Run 5's reads:

```
requirement carry alignment  openai/gpt-5.4-mini  1 (1 live / 0 replayed)  329  36  0.0%  $0.0004
```

Fixed in this branch rather than filed: `align_obligations` now takes a `stage`
argument and `requirement/carry.py` passes `"requirement carry alignment"`. Two
tests cover it, and both were verified to fail with the fix reverted —
`tests/test_stage_attribution.py::test_no_call_into_benchmark_from_the_pipeline_omits_its_stage`
scans for the omission, and
`tests/test_carry.py::test_matching_a_reworded_requirement_attributes_its_model_call_to_a_stage`
drives the carry path, because a call site can pass `stage=` to a client that
never records it.

The scan had a hole rather than a bug: it excludes `benchmark/` on the grounds
that the harness is not part of a review run, and `carry.py` imports out of it.
The scan now follows those imports too, and a companion test pins the crossing
set to exactly `requirement/carry.py: align_obligations`, so a new one is a
visible test edit.

Full suite after the change: 1551 passed, 2 xfailed. `ruff check .` clean on
0.16.2.

## Carried unfixed, both tracked

**The twin pair on `constraint-10`.** It still yields `regenerate-only-nonreusable-sets`
alongside its own obligation, duplicating `constraint-11`'s
`continued-run-produces-only-uncached-sets`, and linking still merges neither.
Left in place deliberately: it is an instance of the open blocker about unmerged
twin obligations starving each other of mapped tests, and leaving it gives Gate 2
a real case of that blocker to assess rather than a synthetic one.

**Two obligation-type slips.** `exclusion-04` typed `docs_config` where its
identically-shaped neighbour got `compatibility`; `completion-07` typed
`regression` where the five requirements of identical shape around it got
`test_demand`. Both carried unchanged from run 3. Recorded against #181, the
decomposition-quality umbrella.

## Cost across the gate

Run 3 spent $0.1638 on 31 calls with nothing to carry. Runs 4 and 5 spent $0.0231
and $0.0117 on 6 and 4 calls, because `--continue` carried 25 and 27 requirements
respectively. Splitting `constraint-10` renumbered three requirements and cost
nothing, which confirms the carry is keyed on requirement text and not on
registry position.
