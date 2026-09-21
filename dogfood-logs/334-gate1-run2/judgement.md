# #334 Gate 1, run 2 — judgement

Run `a1c00b42b03c0fb7`, continuing `7be8d2eaf9d5acd6`. 12 live calls, $0.0463 —
a third of run 1's cost, because 5 of the 7 requirements were carried and only 2
were revised. Worktree `334-sample-candidate-edits` at `0b751b4`.

**Superseded by run 3, and the acceptance below was withdrawn.** See the
correction at the end: this run recorded 15 obligations and printed 14, so the
breakdown reviewed at the gate was not the set the tool held.

**As judged at the time:** accepted, subject to the human's confirmation at the
gate. 14 obligations over 7 requirements. No duplicates, no invented obligations,
none of the real requirements missing, zero open questions.

## What the rewrite changed

Both of run 1's problems went away, and both requirements that moved are the two
the rewrite touched — `2 revised`, which matches.

- The four duplicate pairs under task-02 collapsed to two obligations: the check
  itself, and the refusal rule with the three illustrative cases folded into it
  as examples rather than restated as separate requirements.
- `candidate-edit-makes-defect-true`, the invented `human_review` obligation
  taken from task-01's opening subordinate clause, is gone. Rewording *"When the
  review needs an edit that makes a named plausible defect true"* to *"When the
  review builds an edit for a named plausible defect"* was enough.
- task-01's duplicate pair is gone, but **this does not clear the tool**: the
  rewrite deleted the clause that produced it, so the behaviour is untested here
  rather than shown to be fixed. It stays a drafted filing.

## The obligation set, checked against the mandate

Every behaviour the task file asks for appears exactly once: ask for several
candidates, use the first that passes the existing checks, make the count
configurable, fall back to today's no-edit handling, add the compiled-form
check, refuse a text-different edit whose compiled forms agree, record the three
per-defect counts, report cost and duration, and pick the same candidate on two
runs over the same input. The three Scope exclusions each yield one obligation.

## Zero open questions

Nothing to triage under the gate's three cases. Worth stating plainly rather
than treating as a pass: the mandate deliberately leaves open how the several
candidates are made to differ from one another, and the tool did not ask. That
is the correct outcome under the gate's *implementation detail* case — it is a
decision the builder makes — but it means run 2 provides no evidence either way
about the decomposer's willingness to ask.

## Correction, written while judging run 3

The "14 obligations, no duplicates" above describes the **printed** breakdown.
The decomposition ledger for this run holds **15**. The requirement on the
compiled-form check recorded three obligations and printed two; the one never
shown was `compiled-before-after-compare-compiled-forms`, *"Compile the code
before and after the edit and compare the two compiled forms."*, marked
`importance: critical`.

So this run did carry a third near-duplicate under that requirement, and the
claim that it had no duplicates was wrong. Run 1 has the same shape: 25 in the
ledger, 24 printed, `compiled-before-after-comparison` never shown.

Full detail and the queued filing are in `../334-gate1-run3/judgement.md`.
