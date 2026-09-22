# #334 Gate 2, run 1 — judgement

Run `096837e2e11808db`, base `fdf8254`, head `492a278`, continuing decompose run
`f1594dbe2bba8c92`. $0.6539 over 226 live calls.

**Not clean.** Verdict `INCOMPLETE`, two findings. Both are real; neither is a
tool defect.

## Finding 1 — exclusion 3 is breached, because I worded it wrongly

`no-candidate-test-execution-decision`, from Scope exclusion 3, *"Running the
candidate tests, and anything decided from what they did"*: code evidence **not
addressed**. The review is right. The runner now runs the tests against each
candidate that passes the text checks, and when the run's own gates refuse it —
a broken edit, or one far broader than its defect — it asks for another
candidate. That is a decision made from what the tests did.

But that is what #334 asks for. Its Deliverable says each candidate goes through
"the existing mechanical checks, the control run and the breadth refusal". The
exclusion contradicts the issue; the code follows the issue. What the exclusion
was meant to fence off is narrower: which tests are candidates, and how a run is
performed and read. Disposition: reword the exclusion, which is a mandate change
and re-arms both gates. **Needs the human's call.**

## Finding 2 — nothing tests that the report shows which candidate was used

`which-candidate-it-used`: partially supported, 2 of 3 enumerated defects
killed. The uncovered defect is `candidate-summary-not-rendered-for-all-attempts`,
with 309 pairs put to the model and no killer found. The recommendation asks for
a test that the review output includes the selected candidate for each defect.

Fair. The only report test covers the all-refused case ("none used"). No test
asserts that a successful attempt's report line says which candidate was used —
neither "used candidate 1" nor "used candidate 2" after a refusal. Disposition:
address it with a test.

## What the candidate loop did on its first real review

33 defects. 25 got an edit that passed the gates: **12 on the first candidate,
9 on the second, 4 on the third.** So 13 of the 25 usable edits came from asking
again; before #334 each of those defects would have been `not_mutable`. 7 ended
`no_usable_edit` after three tries, and 1 was `already_present`.

Why candidates were set aside: 20 `failed_check`, 17 `changed_nothing`, 1
`refused_after_run`.

Whether the rescued edits actually make their defects true is not known from
this run — that is #334's audit, on `docs/audit-protocol.md`.

The edit-building stage made 64 calls for 33 defects, cost $0.1866, and took
110.7s of model time. 45% of its prompt tokens were served from the provider's
cache, because later candidates share the first request's opening.

16 of the 25 usable edits ended `not_attempted`: their test runs did not
complete, which on this repository is the nested-pytest hang recorded at #340.

## Unrequested changes — five, all `in_service`, all accepted

The per-candidate report rendering, the `max_candidates` setting, the candidate
bookkeeping and new outcome, the `changes_nothing` helper, and the `seconds`
field on observed calls. Each is part of the delivery.

## Also found, not by the review

Descriptor calls now run inside the 14-wide mutation pool rather than the 8-wide
model-call pool, so up to 14 can reach the provider at once. Fix: a cap inside
`LiveDescriptorBuilder`.
