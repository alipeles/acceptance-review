# #335 Gate 1, run 4 — judgement

Run `4dd305db48e57ea8`, continuing run 3. One change: the repair-edit clause
restated as *"An edit to code that already had the defective behaviour fails the
first half."*

**The breakdown I would defend, with two recorded exceptions.**

## Correct

`evidence-check-defect-truth`, `two-questions-sequence`; the four `task-02`
obligations for the first question; `change-behaviour-to-reach-second-question`,
`edit-must-fail-either-half-refusal`, `already-defective-edit-fails-first-half`;
`passes-both-questions`, `refusal-records-question-and-reason`;
`verification-on-by-default`; the three exclusions; `decision-record-doc-update`.

## Exception 1 — `regression-defect-behavior-before-and-after-edit`

States that the code had the expected behaviour before and the defective after,
as a fact about every edit. The requirement was that the second question *asks*
this; `edit-must-fail-either-half-refusal` carries the refusal. Tool defect,
reproduced in all four runs across three wordings; queued in `docs/DEFERRED.md`
as a drafted filing under #181. At Gate 2 this obligation is expected to read as
unaddressable, and will be judged against that filing, not suppressed.

## Exception 2 — `constraint-01-open-1`, and the missing obligation

A wrong question: the constraint answers it. Reported to the human at the gate
after run 2. Decision: queue a filing (done, under #181, citing #178 and #342)
and continue, carrying the missing obligation — neither question is shown the
tests or what they did under the edit — by hand into Gate 2.
