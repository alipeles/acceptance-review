# Judgement — #228 Gate 2, run 2

**Outcome: INCOMPLETE, and NOT converging. This is the #180 pattern.**

> 2 obligation(s) with non-discriminating test evidence
> (test-all-corpus-cases-pass-check, test-corpus-cases-require-check-before-build).

All three of run 1's findings are resolved. Run 2 names **two different
obligations, with zero overlap** — and both were **strongly supported in run 1**,
over tests that have not changed since.

| Obligation | Run 1 | Run 2 |
|---|---|---|
| `benchmark-no-requirements-fails-naming-case` (task-01) | unsupported | **strongly supported** |
| `test-fails-…-naming-case` (completion-02) | partially supported | **strongly supported** |
| `byte-identical-review-state` | not implemented | moved to exclusion, **confirmed** |
| `test-all-corpus-cases-pass-check` (completion-04) | **strongly supported** | unsupported |
| `test-…-require-check-before-build` (completion-05) | **strongly supported** | unsupported |

The only change to the test file between runs was *adding* one test. Nothing was
removed. The wording of completion-04 and completion-05 is byte-identical across
the two runs.

## The report contradicts itself internally

This is the strongest evidence, and it does not depend on comparing runs.

**Obligation 3** (completion-04, "A test asserts that every case in the
archetype corpus and every case in the decomposition-regression corpus passes
the check") — `unsupported`, `(no mapped test)`, with this recommendation:

> A test is added that iterates over both corpora and verifies each case passes
> the check. […] **detects:** The current tests may only exercise one corpus, or
> only a hand-picked subset.

**Obligation 8** (constraint-04, "The check covers every case in the archetype
corpus and every case in the decomposition-regression corpus") — in the *same
report*, eighty lines later — `strongly supported`:

```
8.6  tests/benchmark/test_empty_registry_guard.py::test_every_archetype_task_file_yields_requirements
8.7  tests/benchmark/test_empty_registry_guard.py::test_every_decompose_regression_task_file_yields_requirements
```

And **unrequested change #5**, in the same report again, describes those very
tests as an *extra*:

> The new test file includes broad corpus-wide assertions that every archetype
> and every decompose-regression case yields requirements, plus a count check
> for corpus coverage.

So one report simultaneously says the corpus-iterating tests do not exist, cites
them as strong evidence, and flags them as surplus to requirements.

## The mapping transcripts show where it happens

Same tests, same obligation texts, different runs:

```
run 1:  test_every_archetype_task_file_yields_requirements
          -> test-all-corpus-cases-pass-check, cover-all-corpus-cases
run 2:  test_every_archetype_task_file_yields_requirements
          -> check-covers-all-corpus-cases, does-not-determine-requirement-text

run 1:  test_an_archetype_case_fails_before_it_materializes_a_repo
          -> test-build-performs-check-before-scoring, pre-score-check-before-build,
             error-instead-of-build-for-no-requirements
run 2:  test_an_archetype_case_fails_before_it_materializes_a_repo
          -> test-failure-uses-supplied-task-file
```

In run 2 the mapper dropped the `test_demand` obligation in both cases and, for
the archetype test, picked up an unrelated **scope exclusion**
(`does-not-determine-requirement-text`) instead.

The pattern: where a Completion expectation ("A test asserts that X") sits
alongside its Constraint twin ("X"), the mapper attaches the tests to one or the
other, unstably, and whichever misses is reported as having no evidence at all.

## Disposition

**Attributed to a tool defect. Queued as a filing against #182** (test discovery
& mapping), cross-referenced to **#180**. Not addressed in code: there is no
test to add. The tests the tool asks for already exist and are cited elsewhere
in the same report.

Writing another test to satisfy obligation 3 would be writing a duplicate of
`test_every_archetype_task_file_yields_requirements` to move a label — the
"fix the output, not the wording" failure CLAUDE.md forbids.

**This is a stop.** Two runs, no overlap, and the second regressed obligations
the first passed. A gate that names a different set each run cannot be converged
on by fixing what it names — the same conclusion #153 and #235 reached, both of
which merged on an explicit human call.

## What is not in doubt

Independent of the gate: the full suite is green (1005 passed), ruff is clean,
and **defect injection confirms the work is real** — short-circuiting
`require_nonempty_registry` fails 8 of the file's tests, including the new
paired control, while the control half keeps passing.
