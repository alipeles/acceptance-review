# 413 Gate 2, run 3 — judgement

Continuing run 2 (`027e2568b87fb680`). The only change since run 2 is
`tests/prompts/test_decomposition_prompt.py`: two helpers and the two tests that
rebuild the gpt-5.4-mini answers. $0.25 on 16 live calls.

Verdict INCOMPLETE. Not clean. I attribute all three findings to tool defects;
drafts are in `docs/DEFERRED.md`. This is the second failure on the same planted
bug, so it goes to the owner rather than to a third attempt.

## Findings

1. **`prompt-test-assertions-hold-on-claude-answers`, still 4 of 5; the bug that
   survived is `assertions-weakened-to-pass-on-claude`** — tool defect (evidence
   judgement). The recommendation's inputs now name the two new tests' exact
   constructions ("constraint-02 plus a copy of completion-02's test_demand
   obligation; exclusion-01 with observable_behavior 'The CSV export's
   supported-currency behavior is unchanged.'"). The tests are not among the
   obligation's mapped tests (10.8–10.11). 148 pairs were put to the model and
   none was judged to catch it. The bug is `not_mutable`, an absence defect, so
   execution cannot settle it either. I verified each new test by breaking its
   helper: only the new test failed.
2. **Two `in_service` unrequested changes** — tool defect. They flag
   `test_every_recording_the_default_replays_is_on_the_default_model` and the two
   rebuilt-answer tests plus their helpers, all added because run 1's and run 2's
   recommendations asked for them. Same family as #376 (a test file cited as
   evidence is reported as an unrequested change).
3. **`recordings-rerecorded-against-new-default`: code evidence addressed ->
   partially addressed** — tool defect (unstable coverage judgement). Its cited
   hunks (9.1–9.4) are identical between runs 2 and 3, and runs 1 and 2 both
   said addressed. Hiding the recordings from review makes this obligation weaker
   to show, as the owner was told when choosing that rule, but that does not
   explain a flip over unchanged evidence.
