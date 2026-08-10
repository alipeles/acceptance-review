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
- No case reaches a scoring hook without having been checked.
- Two runs over byte-identical task text produce byte-identical review state.
- Tests issue no live model calls.

## Scope exclusions
- Which text in a task file counts as a requirement, which is #216.
- How finely a requirement is split into obligations, which is #117.
- How accurately decomposition is measured, which is #211.
- Whether accuracy figures recorded before the archetype corpus was reshaped are
  comparable with later ones, which is #204.
- The wording of the task files already in either corpus.

## Completion expectations
- Implementation
- A test asserts that a case whose task file yields no requirements fails,
  naming the case.
- A test asserts that failure by supplying a task file that yields no
  requirements, rather than by relying on a corpus task file.
- A test asserts that every case in the archetype corpus and every case in the
  decomposition-regression corpus passes the check.
- A test asserts that a scoring hook cannot be reached by a case that was not
  checked.
