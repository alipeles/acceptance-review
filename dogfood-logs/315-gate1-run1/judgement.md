# Judgement — #315, Gate 1, run 1

Run id `b6c50be77e12866f`, at `dc9a22a` (branch `315-defect-set-ground-truth`,
cut from `origin/main`). First decomposition of the mandate; no `--continue`,
so 26 requirements derived from scratch over 29 decompose calls, $0.17.

26 requirements, 25 with obligations, 1 deliberately none. No open questions.

## Was the breakdown accurate?

Mostly. Nothing invented — every obligation traces to a sentence in
`current-task.md` — and no requirement of mine went unrepresented. Two problems.

### 1. My wording, not the tool: the Task sentence produced a fragment

The Task section read *"...reports two failures separately: a way of failing the
review never recorded, and a test the review wrongly predicted would catch one."*
The decomposer split it into three obligations, and the third,
`wrongly-predicted-test-catch`, is the bare noun phrase *"A test the review
wrongly predicted would catch one"* — not a statement about the software, so not
checkable. The second, `missing-failure-mode-recording`, garbled the meaning into
*"reports the failure mode of a review that was never recorded as a separate
failure"*, which is not what the sentence says.

This is the sanctioned rewrite of weak wording. A colon followed by two noun
phrases is not something a decomposer can turn into obligations, and both halves
were already stated properly as constraints 07 and 08, so the Task sentence was
also duplicating them. Rewritten for run 2 as two full statements, with the two
figures left to the constraints that define them.

### 2. A tool defect: `completion-03` mistyped, and the mistype lost a test demand

`completion-03` — *"A test fails when a criterion with no plausible way of
failing is stored so that it cannot be told apart from one the reference set is
silent about"* — is typed `invariant`. Its five siblings of identical form,
`completion-04` through `completion-08`, are all typed `test_demand`.

The mistype has a consequence beyond the label. Because the obligation is not
typed `test_demand`, DR-232's guard against merging a test demand with a
non-test-demand does not fire, so `completion-03` merged into `constraint-02`'s
obligation (`also serves completion-03`). The merged obligation states the
property and demands no test, so the requirement that a test exist for it is
gone from the obligation set — the exact loss DR-232 added the type to prevent.

This is a further instance of the queue entry already open in `docs/DEFERRED.md`,
*"Two obligation-type slips, one of which loses the `test_demand` distinction
DR-232 exists to carry"* (2026-08-29, found at #313's Gate 1). Recorded against
that entry rather than filed separately, with the new fact that the mistype
bypasses DR-232's merge guard. No new backlog item.

Nothing here is fixable by rewording on my side: the sentence is already in the
same form as its five correctly-typed siblings.

## Open questions

None raised. Consistent with the queue entry *"Decomposition has not raised an
open question since #217, because `yielded` and `open_question` are mutually
exclusive"*, filed as #303 — so the absence is a known defect, not evidence that
the mandate is unambiguous. Nothing new to record.

## Disposition

Rewrite the Task section and re-run with `--continue b6c50be77e12866f`. The
type slip stays, being a tool defect with an existing queue entry.
