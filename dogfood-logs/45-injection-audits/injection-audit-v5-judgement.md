# Judgement — injection audit v5 (`openai/gpt-5.4` descriptors)

Judged 2026-09-16 by a helper agent reading every killed and survived edit in
`injection-audit-v5.md` against the source at `518f876`, with no tests run. I
spot-checked two of its calls and both held: the `min` → `max` edit in
`defects/support.py` repairs a defect the code already had, and `report.py` at
`518f876` imports neither `MutationOutcomeKind` nor `TestOutcomeKind`, so edits
naming them raise at render time. The other 58 calls are the agent's and I have
not checked them.

## Counts

| | injects | backwards | unrelated | overbroad | unclear |
|---|---|---|---|---|---|
| killed (47) | 17 | 13 | 10 | 7 | 0 |
| survived (13) | 2 | 4 | 6 | 0 | 1 |

- **backwards:** the defect was already true of the code and the edit repaired it.
  The tests that fail are catching the repair.
- **unrelated:** the edit changes behaviour, but not the behaviour the defect names.
- **overbroad:** the edit makes the defect true but breaks far more — a missing
  import, a validation error, refusing every mutant — so the kill is credited for
  the wrong reason.

## What it means

**17 of 47 kills are credible, and 2 of 13 survivals are real gaps.** The raw
kill count rose from 13 (`gpt-5.4-mini`, v2) to 47, but most of the rise is
edits that do not inject the named defect.

The stronger model fixed the no-op problem (20+ unchanged edits down to 0 that
pass the checks) and the syntax problem, and did NOT fix the backwards problem.
It declined 9 defects as already present, but still edited 17 more defects that
were already true, 13 of which were killed by tests catching the repair.

Two genuine survivals:

- `halted-attempts-lose-specific-reason` — real but low value; the pipeline
  raises before that branch is reachable from a review.
- `execution-tier-changes-conclusions-when-tests-cannot-run` — real; a test
  where every candidate test is set aside would catch it.

## Two failure shapes a mechanical check could catch

1. **An edit that stops the module working at runtime** — a name used but not
   imported. The parse check cannot see it. A kill where every killing test fails
   with `NameError` or `ImportError` is not evidence about the defect.
2. **A backwards edit.** No mechanical check is obvious; this is the one the
   descriptor prompt keeps failing on across both models.

Neither is built. Both are decisions for the human.
