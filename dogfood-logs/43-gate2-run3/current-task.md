# Task

The review can run a named set of a project's tests and observe what each one
does, rather than only reading them. The run happens in an isolated sandbox. A
test that reaches for the network does not reach it. No credential held by the
machine that launched the run is visible to the code under test. The run is
bounded by a time budget, and when that budget is exhausted the run stops
cleanly, leaving nothing still executing behind it.

Every test the run was asked about ends with a recorded outcome: it completed
and passed, it completed and failed, it was blocked reaching the network, it
exhausted its time, or it was never started. An outcome that is not a completed
run carries the reason it is not, so that a test the runner tried and could not
complete stays distinguishable from one it never tried.

A run that does not complete leaves the review's conclusions where they were.
Evidence with no completed run behind it stays at the static tier, and the
review finishes normally rather than reporting an error.

## Constraints
- Only the named tests are run. There is no path through which the whole suite
  runs.
- A time budget applies both to a single test and to the run as a whole.
- The time budgets and the interpreter the tests run under are configuration
  with conservative defaults, and neither is read from the project under review.

## Scope exclusions
- Choosing which tests to run, and deciding whether a project's tests can be run
  at all.
- Altering the code under test in order to observe what a test does.
- Recording which lines a test executed.
