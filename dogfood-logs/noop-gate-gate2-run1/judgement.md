# Comment-and-whitespace gate, Gate 2 run 1 — judgement

Run `18699ec2fcdac462`, base `c1cae87`, head `aa1dd51`. $0.1353 live over 42
calls. First `check` run after #348 (ranked pair judging with a stop rule)
landed on `main`.

**Clean by the gate's definition.** Verdict `NO-MATERIAL-GAPS`. All four
behavioural obligations addressed and strongly supported by discriminating
tests; the three scope exclusions confirmed from code evidence, which is the
only kind that applies to them. No open questions, no recommended tests,
`Recommended next instruction: (none)`. Mandate coverage 6 of 6.

## Evidence ratings

Every behavioural obligation is supported by
`tests/test_mutation_runner.py::TestEveryDefectIsAccountedFor::test_an_edit_changing_only_comments_is_not_mutable`,
at the static tier. That is the right test: it drives `run_mutations` with no
verifier, the default configuration, which is the case the change exists for.
Gate 1 run 2's judgement flagged the risk that "always" had dropped out of the
obligation's description and that a test with verification switched on could
satisfy it; the covering test exercises the off case, so the risk did not
materialise.

Independently of the review, the test was shown non-vacuous before Gate 2:
deleting the new check made it fail with the attempt recorded as `SURVIVED`
rather than `NOT_MUTABLE`, which is exactly the false finding the change
prevents.

## Unrequested changes — four, all accepted

Three `in_service`: the new exported `comparable`, the move of the comparison
into the always-on gate, and the relocation of the layout and suffix constants.
All three are the refactor itself, correctly identified as work the obligations
do not literally request. One `separable`: the extra tests pinning the shared
helper identity and the non-Python fallback. Fair reading; kept, because they
defend the design against the copy drifting back.

## #348 on a real review

For most defects the report reads "4 put to the model, 93 skipped once the
defect was covered", with the skipped pairs recorded as `[defect_already_covered]`
and their ranks named. Every pair is accounted for and the covering test is
named. The covering test ranked 1 to 4 for seven of the eight defects and 12 for
the eighth, consistent with the median first-kill rank of 1 to 3 in
`docs/experiments/rank-prefilter/`. No sign of misranking. No #348 finding.

## The execution tier observed nothing useful

Of eight injected edits, five came back `not_mutable` as identical to what they
replaced, and one fell outside its named region. The two that ran both mutated
the module docstring of `verification.py` and both survived, unverified and
therefore not counted. Correct behaviour — a docstring edit changes nothing —
but it means the ratings here rest entirely on the static judge. Six wasted
edit-building calls out of eight is the problem #334 exists to address.
