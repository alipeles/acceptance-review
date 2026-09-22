# #334 Gate 1, run 6 — judgement

Run `d39591e2b11c3da4`, fresh — no run continued, because continuing run 4 in
run 5 reproduced a revised requirement's old obligation. 15 decompose calls.

**Accepted, subject to the human's confirmation.** 13 obligations over 6
requirements, zero open questions, every derived obligation id printed, no
merges.

Exclusion 3 now yields `exclude-test-candidate-selection-and-run-flow`: *"The
change does not alter which tests are candidates, how the project's tests are
run, or how the result of a run is read."* That fences off what the exclusion
was meant to, and no longer contradicts #334's Deliverable, which has each
candidate go through the checks that run after the tests.

The other twelve obligations match run 4's in substance; several ids differ
(`record-candidate-request-count` is now `candidate-count-recorded`, and the two
other exclusions have new ids), which is expected of a fresh derivation. Future
runs continue from `d39591e2b11c3da4`.
