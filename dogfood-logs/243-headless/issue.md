# #243 — `run_case`'s acceptance test cannot fail — its task file yields no requirements

Child of #186. The sibling of #228 in the runner rather than the corpus.

`test_running_the_empty_skeleton_over_an_archetype_case_yields_an_all_miss_score`
(`tests/benchmark/test_runner.py:35`) is M-B0.2's acceptance test. Its case is
named `archetype-01-missed-obligation`, but its input is not that archetype:

```python
task_text="## Deliverable\nAdd CSV export with active filters.\n",
```

`## Deliverable` is not one of the §7.1 headings `parse_task_file` recognises, so
the paragraph under it lands in `unclaimed` and `build_registry` returns empty.
`run_case` writes this text to a temp file and runs the full checker over it.

The test then asserts `score.gap_recall == 0.0` and calls it "all-miss: the
skeleton found nothing". **That assertion is guaranteed by the input, not by the
checker.** There is nothing in the task file to find, so the test would still
pass against a checker that found every gap perfectly. It is #216's lesson again
— a fixture that cannot fail is not evidence — and #228's inversion again: scored
by a test that never fed a readable input through the pipeline.

`test_run_case_does_not_mutate_the_input_case` (`:73`) uses
`"## Deliverable\n...\n"` and has the same defect, though its assertion (the
input case is untouched) does not depend on the input being readable.

## Why this is not fixed by #228

#228 guards the **corpus case builders** — `build_benchmark_case`,
`build_decompose_case`, `build_corpus_case` — which is the scope its Acceptance
names. These cases are constructed inline in the test and reach `run_case`
without passing through any builder, so #228's guard never sees them.

Placing the guard at hook entry instead was considered during #228's Gate 1 and
rejected: it would fail these tests plus the synthetic cases in
`test_scoring.py`, `test_alignment.py` and `test_case.py`, and deciding what
those should assert instead is this issue's job, not #228's.

## Acceptance

- The M-B0.2 acceptance test runs over a task file that yields a non-empty
  requirement registry.
- Its all-miss assertion fails if the checker under test reports the gaps the
  ground truth labels.
- `run_case` refuses a case whose task file yields no requirements, for the
  reason #228 gives, or the issue records why the runner is exempt.

Related: #228, #216, #202, #204.
