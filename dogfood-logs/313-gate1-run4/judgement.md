# #313 Gate 1, run 4 — judgement

Re-run after rewording the two requirements whose obligations were inverted in
run 3, and splitting the one conjunction whose second half was dropped.

Command: `.venv/bin/acceptance decompose --task current-task.md --continue 747d3c974fc7bc91`
Run id: `2b8741189def35cc`. 29 requirements, 28 with obligations, 1 deliberate
none. 1 derived, 25 carried, 3 revised, 4 decompose calls.

## Not clean. The rewording did not fix either inversion.

**`completion-02` inverted again, on new wording.**

| run | requirement | derived obligation |
|---|---|---|
| 3 | A test fails when the step ... **is given a test**. | A test asserts that the step ... **is given a test**. |
| 4 | A test fails when the step ... **can see any test**. | A test asserts that the step ... **can see any test**. |

The rewrite removed the one thing I thought was my fault — "test" used for two
different things in one sentence. The obligation inverted anyway. Two wordings,
same failure, so this is a derivation defect and not weak wording.

**`completion-06` inverted again.** Requirement reworded to "A test fails when
changing one criterion's text causes another criterion's set to be produced
again." The obligation still reads "A test asserts that a criterion whose text is
unchanged has its set produced again because a different criterion's text
changed" — the same sense, still uninverted, and the obligation id is unchanged
from run 3 (`test-fails-unchanged-criterion-reused-after-other-change`). Both
requirements were among the 3 revised and so were re-derived, not carried; the
4 decompose calls are `constraint-10`, the new `constraint-11`, `completion-02`
and `completion-06`.

## New: splitting the conjunction produced an unmerged duplicate pair

`constraint-10` was cut to "A run continuing an earlier run reuses every set it
is entitled to reuse." It yielded **two** obligations:

- `reuse-entitled-sets-on-continued-run` — "A continuing run reuses every set it
  is entitled to reuse." (correct)
- `regenerate-only-nonreusable-sets` — "A continuing run produces again only the
  sets it is not entitled to reuse." (belongs to `constraint-11`)

`constraint-11` separately yielded `continued-run-produces-only-uncached-sets` —
"A run continuing an earlier run produces again only the sets it is not entitled
to reuse." Linking did not merge that with `regenerate-only-nonreusable-sets`;
neither carries an "also serves" annotation.

This is the paraphrase residue #317's `findings.md` §9 predicted, observed on a
fresh mandate: constraining `source_quote` to the answering requirement's own
spans makes an obligation about another requirement unsourceable but not
unwritable, so misattribution degrades to duplication. `constraint-10`'s call saw
only `constraint-10`'s text, which does not contain what
`regenerate-only-nonreusable-sets` says. The resulting twin pair is the input to
the open blocker about unmerged twin obligations starving each other of mapped
tests.

Trade made knowingly: run 3 dropped half a conjunction, run 4 states both halves
and duplicates one. Stating both halves is the more faithful mandate, so the
split stays.

## New defect: a review-pipeline model call reports its stage as `unknown`

Run 4's usage footer carries a row that run 3 did not:

```
unknown  openai/gpt-5.4-mini  1 (1 live / 0 replayed)  406  60  0.0%  $0.0006
```

Traced: `src/acceptance/requirement/carry.py:168` imports `align_obligations`
from `acceptance.benchmark.alignment` and calls it to match reworded
requirements against prior ones. `benchmark/alignment.py:77` calls
`client.complete(messages, _Alignment)` with no `stage=`, so the call lands in
the bucket `llm.py:46` documents as a defect: *"A review-pipeline call site that
leaves this in place is a defect."*

Three things are wrong at once, and all three are new — the row cannot appear
except on a continued run whose requirement text moved, which is why run 3 did
not show it.

1. It breaks #317's just-landed requirement that a completed run says which
   model each step used. This step says `unknown`.
2. It crosses the layering CLAUDE.md states: *"`benchmark/` is the measurement
   harness; it is not part of a review run."* The review pipeline calls into it.
3. `tests/test_stage_attribution.py` passes (8 passed) with this present, so the
   test written to catch exactly this does not reach the carry path.

## What carried correctly

Splitting `constraint-10` renumbered `constraint-11` through `-13` to `-12`
through `-14`. All three carried unchanged, so the carry is keyed on requirement
text and not on registry position. 25 of 29 carried on 4 calls, against 29 calls
in run 3.

## Findings held from run 3, unchanged

`exclusion-04` still typed `docs_config`; `completion-07` still typed
`regression` rather than `test_demand`. Both carried.

## Disposition

Stop and report. Two rewordings against the same failure is the second attempt,
and a third would be a different approach rather than a fix, so this goes to the
human rather than to a run 5. Nothing here is fixable by wording: the two
inversions survived rewording, the duplicate pair is a linking failure, the
`unknown` stage is a wiring defect in code #317 landed, and the two type slips
are excluded by this mandate's own Scope exclusions.
