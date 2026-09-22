# #335 Gate 1, run 3 — judgement

Run `f8ad97f4cb01bb19`, continuing run 2. One change: the second question now
also requires the expected behaviour before the edit, on the human's decision at
the gate (keep today's check that refuses edits repairing a defect the code
already had).

The task file in this directory was rebuilt from the requirement text echoed in
`output.log`, because the working copy was edited before it was saved here. The
`task-03` text in the log is the authority.

## task-03

- `edit-must-fail-either-half-to-be-refused` — the refusal now yields an
  obligation. Correct.
- `regression-defect-behavior-before-after` — still a claim about every edit
  rather than about the software. Same defect as runs 1 and 2, already queued.
- `repairs-existing-defect` — *"The change includes an edit that repairs a
  defect the code already had."* Wrong: the clause named a kind of edit that is
  refused. My wording invited it (a trailing "including one that…" after
  "refused"), so reworded for run 4. Also the same shape as the queued defect:
  the operator ("is refused") is dropped and the content kept. Added to that
  filing's evidence.

Everything else carried unchanged from run 2.
