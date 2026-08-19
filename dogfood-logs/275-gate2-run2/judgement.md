# Judgement — #275, Gate 2, run 2

`check --task current-task.md --base bcbed91 --head 5f50f64 --mode record`.
SHAs in `revisions.txt`. Re-run because run 1's findings were acted on, which
re-arms the gate.

**Clean by the gate's definition.**

```
Task completion: NO-MATERIAL-GAPS

25 obligation(s) addressed and strongly supported by discriminating tests;
6 boundary obligation(s) confirmed from code evidence, which is the only kind
that applies to them.
```

| gate condition | result |
|---|---|
| every obligation addressed | yes — 31 of 31; nothing `not_addressed`, `partially_addressed` or `unclear` |
| every obligation strongly supported | yes — 25 `strongly supported`; the other 6 are the scope exclusions, `code_only` with a recorded reason (#266), which the verdict counts as satisfied rather than unmeasured |
| every open question resolved | yes — none was raised |
| no recommended tests | yes — zero |
| nothing else needing attention | two `in_service` unrequested changes, discussed below |

Mandate coverage 32 of 33; the one requirement yielding nothing is
`completion-01` ("Implementation"), a bare section marker, declined
deliberately.

## The mapping behind the verdict was checked (DR-164)

A clean verdict over a half-blind mapping is worth nothing, so:

- **no obligation carries "(no mapped test)"** — zero occurrences in the report;
- every `strongly supported` block cites specific test ids (44 citations);
- across the run's mapping calls, several batches returned substantial
  `obligation_ids` (30, 28, 25, 17, 15, 10 ids). Batches that came back entirely
  empty are candidate tests that genuinely bear on nothing in this mandate —
  discovery offers 12 tests per call from a 1,161-test suite.

## The caveat that belongs on this result

**Twenty ratings moved from `partially supported` to `strongly supported` on a
test-only change.** The source diff is byte-identical between run 1 and run 2;
only `tests/coverage/test_recommendations.py` and
`tests/test_recommendation_omission.py` differ, by 57 added lines.

Three of those twenty had a concrete gap that the new tests genuinely close. The
other seventeen were held down by unfalsifiable "might fail for some other case"
defects (run 1's judgement lists them), and no test can close those — yet they
cleared. So the honest reading is that the rating responded to the *presence of
more test material*, not only to the specific gaps named. That is #180/#252
rating instability, and this pair is an unusually clean instance of it: same tool
version, same task file, same source diff, one variable changed.

The two runs are a controlled A/B and are queued as a comment on #252.

The unrequested-change list moved the same way and the same distance: run 1
reported **seven** entries including one `risky` (the `recommend_tests` signature
change); run 2 reports **two**, both `in_service`, over the same source diff.

## Unrequested changes — two, both `in_service`

1. The `RecommendationResult` wrapper and the widened
   `report.py` / `recommendation.py` surface. A correct observation about a
   design decision the mandate did not spell out; it is not separable, because
   the mandate requires the stage's result to distinguish a prescription from
   one that was not obtained and a bare list cannot carry the second.
2. `tests/test_recommendation_omission.py` carrying more assertions than the
   listed completion expectations demand — retrieval formatting, persistence,
   determinism. Advisory, and the extra assertions are the wiring tests CLAUDE.md
   asks for.

Neither is `separable` or `risky`, and neither affects the verdict (M7.6
advisory presentation).

## What this run does not establish

The verdict is bounded, as §3.7 requires: no material gaps at the achievable
tier, over a static review with no execution. The recommendation stage's own
behaviour under a real partial response was exercised by injected responses in
tests, not by a live model omitting a criterion — that live instance is the one
in `dogfood-logs/258-gate2-run2/`, and re-running #258's Gate 2 on top of this
change is what will confirm the fix on the case that produced it.
