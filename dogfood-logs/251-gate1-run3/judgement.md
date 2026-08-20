# Judgement — #251 Gate 1, run 3

34 requirements, 33 obligations, one requirement deliberately given none
(`completion-01`, the bare `Implementation` section marker). Zero open questions.

**Result: accepted as the Gate 1 breakdown.** Every obligation traces to a
requirement in the mandate, and every requirement is represented. All six Scope
exclusions now render with their sense intact. Two residual redundancies are
recorded below; neither invents an obligation nor loses one.

## What the rewordings fixed

Run 1's inverted `exclusion-05` and duplicate-description pair, and run 2's
inverted `exclusion-01`, are all gone. Three requirement pairs that had stayed
separate in run 2 merged here: `constraint-01`↔`completion-02`,
`constraint-02`↔`completion-03`, `constraint-07`↔`completion-05`.

## Residual redundancy 1 — an unreconciled linking triangle

Reported by the tool itself:

```
Unreconciled linking answers: answers contradict each other: these obligations
are linked transitively but at least one pair among them was denied, so none of
them were merged
  affected: changed-rating-must-name-a-change, changed-rating-names-one-given-change,
            changed-rating-justifies-itself
```

Those three (from `completion-07`, `constraint-11` and the Task prose) are one
claim stated three ways. Linking denied one pair of the three, and the
reconciliation rule then merged none of them, leaving three obligations where
there is one requirement. Conservative and honestly reported, but it means the
same claim will be mapped, judged and rated three times at Gate 2.

**Not a stop.** The gate's test is that no obligation is invented and none is
missing; a claim represented three times is neither.

## Residual redundancy 2 — `constraint-16` and `completion-10` did not merge

They say the same thing ("A review repeated over the same stored state and the
same inputs produces the same review state as the one before it" /
"Two reviews over the same stored state and the same inputs produce
byte-identical review state") and merged in run 2. Here they did not.

## The measurement worth keeping from this sequence

Run 2 → run 3 changed **one bullet**, in `## Scope exclusions`, and it inverted
the merge outcome for five requirement pairs that were not touched:

| pair | run 2 | run 3 |
|---|---|---|
| `constraint-16` ↔ `completion-10` | **merged** | not merged |
| `constraint-01` ↔ `completion-02` | not merged | **merged** |
| `constraint-02` ↔ `completion-03` | not merged | **merged** |
| `constraint-07` ↔ `completion-05` | not merged | **merged** |
| the three-way triangle above | unreconciled (different members) | unreconciled |

Both runs' inputs and full outputs are committed under `dogfood-logs/251-gate1-run2/`
and `-run3/`, so the pair is reconstructable.

**Corrected by run 4 — read `dogfood-logs/251-gate1-run4/judgement.md`.** This
judgement originally read the inversion as #231's defect reproduced at the
linking stage, and asserted that linking has no equivalent protection to #269's
carry key. That was wrong: `linking.py:482-500` carries a merge decision forward
whenever both its obligations are unchanged (#269's `constraint-32`). Runs 1–3
never engaged it, because none of them passed `--continue`. Run 4 replays this
same task file naming run 2 as the continued run and reproduces run 2's merge
outcome exactly.

The instability above is real for any run that does not name a continued run —
which is every run the documented Gate 1 procedure produces — but it is #269's
design operating as specified, not a gap in it. What survives is a documentation
change to the Gate 1 command, queued in `docs/DEFERRED.md`. No issue filed.

## Open questions

None raised across all three runs, so the gate's three-case triage table has
nothing to apply. Worth stating plainly rather than leaving as silence: this is
the first mandate in recent memory to raise none, and the reason is probably that
its Constraints were written one claim per bullet from an issue that had already
been argued out, not that the decomposer stopped asking.
