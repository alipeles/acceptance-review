# Judgement — injection audit v8 (surrounding code shown to the edit-building call)

Judged 2026-09-17 by a helper agent reading every edit and claim in
`injection-audit-v8.md` against the source at `518f876`, by the same categories
as the v6 and v7 judgements. I hand-checked three entries where v7 and v8
disagree (below).

The only change from v7: both mutation-stage model calls are shown M2.2's
bounded surrounding code — each region's enclosing definition and its in-repo
call sites, test files withheld (`13b7c6d`). Same 64 defects, same 22 criteria,
edits on `openai/gpt-5.4`.

## The table

| | v6 (22 criteria) | v7 | v8 |
|---|---|---|---|
| edits counted (kills and survivals) | 58 | 44 | 48 |
| put the named defect into the code | 25 (43%) | 25 (57%) | 25 (52%) |
| repair a defect the code already had | 7 | 3 | 4 |
| change something other than the defect | 16 | 12 | 17 |
| break far more than the defect | 10 | 4 | 2 |
| real kills | 20 of 46 (43%) | 23 of 36 (64%) | 21 of 39 (54%) |
| real survivals | 5 of 12 | 2 of 8 | 4 of 9 |
| edits refused by a check | — | 8, all correctly | 7, one wrongly |
| already-present claims | — | 12: 9 right | 9: 9 right |

**The surrounding code did not improve the edits.** On the measures that matter
it is level or slightly worse than v7, and a single run each cannot separate a
5-point move from noise. It did not make things much worse either.

Two smaller changes: edits that break far more fell again (4 → 2), and two edits
came back byte-identical to their input, which v7 had at zero.

Of the 9 already-present claims, **all 9 are right** (v7: 9 of 12). Only 1 of the
9 repair edits repairs the code; 5 do not and 3 gave no usable repair.

## What I hand-checked

- **`region-containment-check-too-permissive`** — the two runs produced the
  *identical* edit and the two judging passes disagreed. Reading it myself, v8 is
  right and v7 was wrong: the defect's defective behaviour explicitly includes
  "the containment test is effectively reversed", and the edit reverses it. **So
  the breadth check refused a genuine injection.** It failed 26 tests because
  every injected edit passes through that one check, not because it broke
  something unrelated. The breadth check's cost is not zero, and this is its
  first measured false refusal.
- **`parserless-files-still-rejected`** — the two runs produced *different*
  edits. v8's returns "no parser available" as an invalidity reason, which is
  exactly the defective behaviour. Judged right in both runs.
- **`allow-failing-tests-not-propagated`** — different edits again. v7 set
  `execution=None`, disabling the whole tier; v8 set `allow_failing_tests=False`,
  which is precisely the defect. Judged right in both runs.

So one of three sampled disagreements is a judging error, and the other two are
the arms genuinely producing different edits — sometimes sharper in v8.

## Retrieval budget

The retrieval scanned 200 files and stopped. I verified the cut falls inside
`tests/`, so all of `src/` was scanned and only test files were lost — and those
are withheld from the call anyway. The budget did not weaken this arm.

## What the judge noticed twice, in both runs

Every defect whose stated expected behaviour the mutation stage fails is one the
code fails *by design*: the evidence-tier ladder, halting on tests that already
fail, keeping edits inside the named regions. Those criteria look wrongly derived
rather than wrongly implemented, which is the human's open adjudication.

And at least six edits answered "expected" started from code already in the
defective state, so the model misread the code rather than writing a bad edit.
The surrounding code did not fix that.
