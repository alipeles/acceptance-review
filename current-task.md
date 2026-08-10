# Task
A benchmark case whose task file yields no requirements fails, naming the case,
instead of being scored.

## Constraints
- A benchmark case whose task file yields no requirements raises an error rather
  than being built.
- The error names the case it was raised for.
- The error says the case did not run, so the outcome cannot be read as a score
  of zero.
- The check covers every case in the archetype corpus and every case in the
  decomposition-regression corpus.
- A case built from either corpus is checked before it can be scored.
- Tests issue no live model calls.

## Scope exclusions
- Which text in a task file counts as a requirement, which is #216.
- How finely a requirement is split into obligations, which is #117.
- How accurately decomposition is measured, which is #211.
- Whether accuracy figures recorded before the archetype corpus was reshaped are
  comparable with later ones, which is #204.
- The wording of the task files already in either corpus.
- Whether two runs over byte-identical task text produce byte-identical review
  state, which this change neither strengthens nor weakens.

## Completion expectations
- Implementation
- A test asserts that a case whose task file yields no requirements fails,
  naming the case.
- A test demonstrates that failure with a task file the test supplies, not with
  a task file taken from either corpus.
- A test asserts that every case in the archetype corpus and every case in the
  decomposition-regression corpus passes the check.
- A test asserts that a case cannot be built from either corpus without the
  check being performed.
