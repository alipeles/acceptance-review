# Judgement — #251 Gate 1, run 4

Run 3's task file, byte-identical, decomposed again with
`--continue 1e1f030192c9884b` — run 2's run id. This is the run that was missing
from runs 1–3, and it corrects a wrong conclusion drawn from them.

Command:

```
.venv/bin/acceptance decompose --task dogfood-logs/251-gate1-run3/current-task.md \
    --mode record --continue 1e1f030192c9884b
```

Header: `requirements: 34 derived? no — 2 derived, 31 carried, 1 revised;
1 decompose call(s)`. Runs 1–3 each reported `0 carried, 0 revised` and 5
decompose calls.

## What it establishes

**#269's carry-forward covers de-duping, not only derivation.**
`linking.py:482-500` carries a merge decision forward whenever both obligations in
the pair are unchanged — #269's `constraint-32`, *"A merge decision over two
obligations that are both unchanged is carried forward without a model call."*
Run 4 reproduces run 2's merge outcome exactly:

| pair | run 2 | run 3 | run 4 |
|---|---|---|---|
| `constraint-16` ↔ `completion-10` | **merged** | not merged | **merged** |
| `constraint-01` ↔ `completion-02` | not merged | **merged** | not merged |
| `constraint-02` ↔ `completion-03` | not merged | **merged** | not merged |
| `constraint-07` ↔ `completion-05` | not merged | **merged** | not merged |

## The wrong conclusion this corrects

`dogfood-logs/251-gate1-run3/judgement.md` recorded the run 2 → run 3 inversion as
#231's defect reproduced at the linking stage, and asserted that linking "has no
equivalent protection" to #269's carry key. **That is wrong.** Linking has the
gate; runs 1–3 simply never engaged it, because none of them named a continued
run. The measurement was of the tool with the relevant feature switched off.

The instability itself is real and reproducible — it is what any run that does not
name a continued run gets, and that includes every Gate 1 run this repo's
documented procedure produces. But it is #269's design operating as specified
(*"No obligation is carried forward when no continued run is named"*), not a gap
in it.

## What survives as an action

A documentation change to `CLAUDE.md`'s Gate 1 step, so a gate's re-runs pass
`--continue`. Queued in `docs/DEFERRED.md`. No issue filed.

## Cost of the correction

One live `align_obligations` call, which had no recorded transcript: run 3's task
file has one requirement whose text differs from run 2's, so the residue between
the two registries needed the alignment judgement that tells an edited requirement
from a new one. The other 31 requirements carried without a call.
