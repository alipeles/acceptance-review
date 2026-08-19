# Judgement — #269 Gate 2, run 3

`check --task current-task.md --base 9def9e7 --head 7fc842d`, branch
`269-decompose-carry-forward`.

**Gate 2 is BLOCKED, and #269 is not at fault.** The review aborts before
rendering:

```
acceptance: model error: no recommendation for 2 of 49 weak obligation(s):
carry-forward-unchanged-merge-decisions, reask-merge-decision-when-either-obligation-changed
```

**No report exists**, so Gate 2 cannot be assessed at all — not clean, not
unclean, unknown. Reproduced identically on a replay re-run, so it is
deterministic rather than a bad draw.

## This is #266's abort, still reachable after #271 closed it

The raise is `coverage/recommendations.py:196`. The comment immediately above it,
written by #271, states the reasoning that was supposed to make it unreachable:

> Every obligation reaching here requires test evidence, decided at
> decomposition. So silence is once again the only thing this has to reject —
> there is no correct reason for the model to skip one, and no second list in
> which it might have answered instead (#266).

The premise may well be right and the conclusion still does not hold: the model
skipped two of forty-nine anyway, and one skipped recommendation destroys the
entire review — 47 answered obligations, all coverage work, and the verdict, none
of which reaches the user. #258 was blocked on this for a week and #271 landed to
unblock it. It is back.

**Runs 1 and 2 of this gate rendered fine**, at 44 and 49 weak obligations
respectively, so this is not a hard threshold. It fires on a large batch
sometimes — which is #258's transcript finding restated: partitioning does not
fix this, it only shrinks how much each abort destroys.

## The second defect, which is the more interesting one

Both aborting obligations were **`strongly supported` in run 2 of this same
gate**, one commit earlier:

| obligation | run 2 | run 3 |
|---|---|---|
| `carry-forward-unchanged-merge-decisions` | strongly supported, citing 2 tests | not strongly supported |
| `reask-merge-decision-when-either-obligation-changed` | strongly supported, citing 2 tests | not strongly supported |

`weak` is defined as *not-strongly-supported and requiring test evidence*
(`recommendations.py:139-142`), so both dropped out of `strongly supported`
between the two runs.

**Their evidence did not change.** The run-3 commit touched
`requirement/obligations.py` and added two tests to
`tests/requirement/test_carry_forward.py`. It did not touch
`requirement/linking.py`, and it did not touch either of the four tests these two
obligations cited in run 2 — all of which still exist and still pass
(1186 passing).

So a rating moved from `strongly supported` to weak while the code under review,
the obligation text and the cited tests all stood still. The only thing that
moved is unrelated content in the same diff and the same test file.

## Dispositions

Both are tool defects, both outside #269's area, and both are drafted as filings
in `docs/DEFERRED.md`:

1. **The abort survives #271** — `coverage/recommendations.py`, umbrella #185.
   Blocker: it is the difference between a review and no review.
2. **A rating flips on unchanged evidence** — evidence judgement, umbrella #183.
   Related to #251 (re-judge only when inputs changed) and #252.

Neither is fixed here. #269 has not touched `coverage/` or `evidence/`, and
fixing the recommender inside this issue would be a second delivery hiding in
one branch.

## What is known about #269 itself, from run 2

Run 2 rendered, and it is the last full picture available. It reported
`INCOMPLETE` on two obligations, **both of which were real gaps in my work and
both now closed** (`8e6a934`, `7fc842d`):

- `schema-change-blocks-carry-forward` — no test existed. Two now do, and both
  injections were confirmed to fail them.
- `revised-requirement-records-revision-reason` — **a defect, not a missing
  test**: a revised requirement's disposition reported `derived` and carried no
  reason, indistinguishable from a genuinely new requirement. Fixed by
  `_stamp_revisions`.

Run 2 also showed every other obligation addressed, and the merge-decision pair
strongly supported. That is not a clean Gate 2 and must not be read as one — the
run that would say whether the fixes landed clean is the one that aborts.

## Status

**Stopped.** Presenting at the gate. #269 sits unmerged, as #258 did, until the
recommender defect is fixed.
