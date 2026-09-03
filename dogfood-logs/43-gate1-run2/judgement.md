# Judgement — #43 Gate 1, run 2

**Command:** `.venv/bin/acceptance decompose --task current-task.md --continue 9a43f4a351b5c204`
**Run id:** `e1a0e28ecd9479c7`, continuing `9a43f4a351b5c204`
**Task file SHA context:** branch `43-sandbox-runner`, at `a520d67` (tip of
`main`); `current-task.md` uncommitted at the time of the run.
**Cost:** $0.0159 on 6 live calls.

## Result

**Gate 1 passes.** 9 requirements, all with obligations, 18 obligations in
total, no duplicate pair, no open questions.

8 requirements were carried unchanged and 1 was revised — `task-03`, the only
one whose wording changed between runs. That is the behaviour `--continue` is
supposed to give: the untouched requirements did not move for reasons unrelated
to the edit.

The run also reproduces the cost figure CLAUDE.md cites for continuing a run:
6 calls and $0.0159 here, against 23 calls and $0.1171 for run 1 over nearly the
same file.

## What the rewrite fixed

Run 1's `task-03` yielded four obligations, one of which — "Treat this as an
ordinary result rather than a failure" — did not say what it was about. Run 2's
`task-03` yields three, each of which states its own subject:

- `conclusions-unchanged-on-incomplete-run`
- `static-tier-for-unrun-evidence`
- `review-finishes-normally`

**This does not clear the tool defect, and it is worth being blunt about what the
rewrite cost.** The defect is that the decomposer dropped an antecedent its input
carried and emitted an obligation with no subject, silently. Rewording the input
removed the trigger, not the defect, and it means the only surviving evidence is
run 1's committed log. The drafted issue in `docs/DEFERRED.md` — a new child of
#181, the decomposition umbrella — carries it, together with three earlier
instances found in the committed logs of #251 and #261 that no rewrite of this
task file touches.

An earlier version of this judgement called the run-1 pair a duplicate left
unmerged and attributed it to #304, the issue on colliding ids. That was wrong:
with the referent missing, whether the two obligations say the same thing cannot
be determined by reading them.

## Accuracy of the breakdown

I read all 18 obligations against the task file. None is invented, and every
requirement the file states is represented. Two judgement calls worth naming:

- "leaving nothing still executing behind it" did not become its own obligation.
  It is folded into `clean-timeout-stop`, which is defensible — the clause
  defines what "cleanly" means rather than adding a separate requirement.
- The five outcome kinds task-02 lists (passed, failed, blocked reaching the
  network, exhausted its time, never started) are not decomposed one per
  outcome. They are treated as the definition of `test-outcome-recorded`. I
  accept this: the alternative is the pre-enumeration the task-file style rules
  warn against.

## Open questions

None raised, same as run 1, and the same reading applies: the file leaves the
network-blocking mechanism, the default budget values and the storage location
open on purpose, and those are implementation details for the coding agent.
