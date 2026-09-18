# #340, Gate 1, run 5 — the breakdown I am prepared to defend

Run `e0c0ad243a8456ef`, continuing `3dfa03e43b7edb95`. 13 requirements, 0
derived, 11 carried, 2 revised, 28 obligations. **No open questions raised.**

## The set is accurate

Every obligation traces to a sentence I wrote, and every sentence I wrote is
represented. Nothing is invented and nothing real is missing. Both of run 4's
problems are fixed:

- `run-project-tests` (`test_demand`) is replaced by `test-worth-doing-review`
  and `pair-drop-counting`, neither of which is a demand for a test. #325 — the
  filed defect where a `test_demand` criterion is never enumerated for and so
  stays permanently indeterminate — no longer applies to this set.
- The pronoun-stripped obligations are gone. `task-04` now yields five obligations
  that each stand alone: `dropped-pair-not-decided`, `state-dropped-pair-as-dropped`,
  `dropped-pair-drop-reason-recorded`, `injection-attempt-basis`,
  `dropped-pair-not-demonstration-of-test-failure`.

## Two things I left alone deliberately

`inject-edit-for-each-plausible-defect` and `run-candidate-tests-against-edit`
come from my opening sentence, which describes behaviour the review already has.
They are obligations this change does not deliver. I left them because they are
true, testable, and already covered by the existing suite, so they cost a
judgement and mislead nobody. Removing the sentence would leave the rest of
`task-01` without an antecedent.

`red-test-does-not-identify-defect` came from a *because* clause. Kept for the
reason run 3's judgement gives: it states a real invariant of the design.

## The one thing to surface, not resolve

`test-worth-doing-review` is typed `human_review` — *"The review decides whether
running the project's tests is worth doing."* `CLAUDE.md`'s rule that anything
marked as needing human review is a pause applies, so it is surfaced at the gate
rather than decided here. It restates a property the code already has
(`mutation/settings.py::decide_execution`), so I expect it to be satisfied by the
change to that function rather than to need non-code evidence — but that is my
belief, not a verification.

## Cost

Runs 3, 4 and 5 spent nothing live; every call replayed. The corpus for this task
file cost $0.1955 to record at run 2 and $0.0455 more by run 5.
