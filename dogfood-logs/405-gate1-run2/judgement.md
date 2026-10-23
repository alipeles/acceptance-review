# #405 Gate 1, run 2 — judgement

Run `4c120edcd9cd9bd2`, continuing run 1. 8 requirements, 21 obligations, 0 open
questions.

Run 1's defect is gone: `task-01` now yields the three outcome obligations.
"Never prints their values" now has an obligation (`hide-env-var-values`).

**Not accepted, my wording.** "The tool does not guess an interpreter or a
directory" in the task body and "Working out a test command from the project's
files" in Scope exclusions stated the same requirement twice, and produced two
obligations (`do-not-guess-interpreter-or-directory`,
`do-not-work-out-test-command-from-files`). Removed the body sentence and
widened the exclusion (run 3).

Tool observation, carried to run 3: `hide-env-var-values` restates all of
`print-env-var-names` and adds "while hiding their values".
