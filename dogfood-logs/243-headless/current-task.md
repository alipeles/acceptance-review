# Task

The benchmark runner, `run_case` in `src/acceptance/benchmark/runner.py`, feeds a
benchmark case's task file, repository and revisions through the full checker
and returns a scored copy of the case.

`run_case` must refuse a case whose task file yields no requirements, raising the
same `EmptyRequirementRegistryError` the corpus case builders raise, before any
checker stage runs. A case whose task file yields requirements runs through the
checker and is scored.

The runner's acceptance test, which runs a checker that finds nothing over a
missed-obligation archetype case and asserts an all-miss gap score, must run over
a task file that yields at least one requirement. A companion regression test must
run the same case through a checker that reports the labelled gap, and show the
gap recall is then non-zero, so the all-miss assertion is shown to depend on the
checker's output and not on the input.

## Constraints

- The refusal uses the existing `require_nonempty_registry` check, so the runner
  and the corpus case builders agree on what counts as a readable task file.

## Scope exclusions

- The synthetic cases in the scoring, alignment and case tests, which build
  scored cases without calling `run_case`.
- The corpus case builders, which already refuse an unreadable task file.

## Completion expectations

- Implementation
- Regression test
