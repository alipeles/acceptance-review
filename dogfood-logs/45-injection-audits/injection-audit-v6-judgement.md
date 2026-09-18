# Judgement — injection audit v6 (defects as expected and defective behaviour)

Judged 2026-09-16 by a helper agent reading every killed and survived edit in
`injection-audit-v6.md` against the source at `518f876`, with no tests run, by
the same categories as `injection-audit-v5-judgement.md`. I spot-checked two
calls and both held: `strongest-tier-computed-as-weakest-tier` repairs code that
already did the defective behaviour, and `no-search-for-smaller-edit` wraps a
value in `next(iter([x]), None)`, which changes nothing. The rest are the
agent's calls and I have not checked them.

What changed from v5: defects re-listed over the same 25 criteria and the same
diff, each now carrying `expected_behavior` and `defective_behavior`, and the
edit-building prompt deciding direction from them (commit `0ece5c3`). Edits on
`openai/gpt-5.4` in both runs. The defects are not the same ones — 74 now, 71
then — so this compares rates, not individual defects.

## Edits that actually put the named defect into the code

| | v5 (one sentence) | v6 (two behaviours) |
|---|---|---|
| edits judged | 60 | 66 |
| inject the named defect | 19 (32%) | 31 (47%) |
| repair a defect the code already had | 17 | 9 |
| change something other than the defect | 16 | 16 |
| break far more than the defect | 7 | 10 |
| credible kills | 17 of 47 | 25 of 53 |
| real test gaps among survivals | 2 of 13 | 6 of 13 |

## What it shows

**Better, not good enough.** Repairs halved and credible results rose from about
a third to about half, but more than half of what injection would settle is
still wrong.

**The edit-building model still ignores the direction it is given.** In the
remaining 9 repairs the code already did the DEFECTIVE behaviour, the prompt
says to answer `already_present` in that case, and the model edited toward
EXPECTED anyway. `no-search-for-smaller-edit` is the same failure ending in an
edit that changes nothing instead of a repair.

**Some expected behaviours contradict the design.** The weakest-tier pairs, the
halt on a failing candidate test, and execution being opt-in: the listing step
wrote as EXPECTED something the code deliberately does not do. Those are
arguably real findings about the code, or wrong criteria — a human call — but
either way an edit toward EXPECTED is not an injection.

**Pair quality is mostly fine:** 62 of 74 pairs are about one point in the code
and contradict each other; 12 are vague or about two different things.

**Edits that change nothing are now the main survival problem:** 5 of the 6
unrelated survivals leave behaviour identical, which reads as "the tests missed
this defect" when nothing was injected.

**10 edits break far more than the defect**, mostly by crashing on
`AttributeError`, `TypeError` or a validation error. The check added in
`0500eb2` covers only `NameError` and `ImportError`, so these still count as
kills.

## Real test gaps among the survivals

- `not-attempted-defects-never-fed-to-static-judge`
- `execution-tier-overrides-static-when-run-is-unavailable`
- `descriptor-response-shape-can-lose-span-bounds`
- `halt-reason-not-emitted-to-caller`
- `prediction-language-still-used-in-recorded-conclusion`
- `no-discriminate-report-not-wired` (narrow)

Of 4 `already_present` answers, 3 are right.
