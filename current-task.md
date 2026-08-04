# Task
Stop pushing a recommendation file nobody asked for, and let an agent pull the
detail when it decides to act. Today a review with gaps writes its next
instruction to one fixed path in the repo. That path is keyed to no task and no
revision, so whichever run last found gaps owns it; a later clean run leaves it
untouched, and the file then contradicts the report while only the report is
telling the truth. The content is also a second, lossier copy of recommendations
the review already carries as structured fields. Replace the written file
`.acceptance/next-instruction.md` with `acceptance recommendation --criterion
<id> [--format json|text]`, which returns a criterion's recommendation from
stored review state on demand, defaulting to JSON.

The command surface is fixed here rather than left to implementation: the
specification has to name a specific command, and a document written against a
command that later changes would recreate the same two-artifacts-drifting
failure this task exists to remove.

## Constraints
- Nothing is written speculatively, so nothing can go stale.
- A recommendation returned on demand is the one the stored review holds for that
  criterion — retrieval reads state, it does not re-run the review.
- The structured fields keep their prose values. Compressing a field to a terse
  token loses the reasoning that makes the recommendation actionable.
- A reader of the review's own output can tell how to obtain the detail; if the
  output does not make the detail's existence known, the pull never happens.
- A repo that already contains `.acceptance/next-instruction.md` from an
  earlier version is left in a state where nothing on disk contradicts the
  review.

## Scope exclusions
- What the recommendations themselves contain is unchanged; this task moves how
  they are obtained, not how they are produced.
- The review-state store's format and the review pipeline are unchanged.
- Recording that this task supersedes the earlier one belongs to the issue
  tracker, not to any file in this repo.

## Completion expectations
- Implementation
- `acceptance recommendation --criterion <id>` returns that criterion's
  recommendation from stored review state, without re-running the review.
- The retrieved recommendation carries each structured field as a discrete key
  — required inputs, boundary conditions, expected output, required assertions,
  plausible defect, repo conventions — with their prose values intact.
- A criterion that has no recommendation returns an empty result rather than an
  error.
- Retrieval defaults to the most recently stored review when the caller does not
  name one.
- No code path writes `.acceptance/next-instruction.md`.
- A run that finds an `.acceptance/next-instruction.md` left by an earlier
  version removes it and reports that it did so.
- Starting from a repo that already contains `.acceptance/next-instruction.md`,
  a clean run leaves the review's own output as the only statement of status.
- The review's rendered output names the command to run, not a file to open, for
  every verdict that has gaps.
- Two retrievals over unchanged review state return byte-identical output.
- The specification no longer describes the recommendation as a written file.
