# #334 Gate 1, run 2 — judgement

Run `a1c00b42b03c0fb7`, continuing `7be8d2eaf9d5acd6`. 12 live calls, $0.0463 —
a third of run 1's cost, because 5 of the 7 requirements were carried and only 2
were revised. Worktree `334-sample-candidate-edits` at `0b751b4`.

**Accepted, subject to the human's confirmation at the gate.** 14 obligations
over 7 requirements. No duplicates, no invented obligations, none of the real
requirements missing, zero open questions.

This acceptance was withdrawn for a few hours on 2026-09-21 and then reinstated.
The correction at the end of this file explains why: the withdrawal rested on a
misreading of the ledger, not on anything wrong with this run.

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

## Correction — an alarm I raised and then withdrew

While judging run 3 I noticed that this run's ledger lists **15** obligations
under `derivations[].obligations` while the breakdown printed **14**, and
concluded that the renderer was hiding one. That was wrong, and it cost the
human a withdrawn confirmation.

**The two numbers count different things.** `derivations[].obligations` records
what each requirement *derived*, before linking. The breakdown renders what
survived. This run's ledger holds exactly one `merge_decisions` entry, with
`same_requirement: true`, and I recomputed its two fingerprints — sha256 over
id, description and observable behaviour, per `ledger.py::obligation_fingerprint`
— against every obligation in the run. They are `compiled-form-change-check` and
`compiled-before-after-compare-compiled-forms`.

So the pair was recognised as one obligation and merged, which is decomposition
working. 14 is the true set. Run 3's report of "3 obligation(s) dropped" counts
derivations, and is likewise correct.

**What went wrong in the judging, for the next person.** I compared two counts,
formed a hypothesis about the renderer, and reported it as a finding without
reading the code behind either number. The hypothesis was labelled as unverified
and still filed as a blocker. Reading `cli.py::_requirement_block` would have
shown in a minute that it iterates the requirement map's dispositions rather
than the obligation set, which rules the renderer out immediately.
