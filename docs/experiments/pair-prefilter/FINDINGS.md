# Prefilter the pair set — findings

**The best filter excludes 22.0% of the 12,450 pairs without skipping a recorded
kill, using `voyage-code-4` on both sides.** That is not enough to adopt on its
own, but it is enough to make a held-out check worth running — which the earlier
`voyage-code-3` result, at 14.6%, was not. The model choice turned out to matter
more than anything else tried here.

Measured on #314's Gate 2 run: **12,450 pairs, 127 kills, a 1.0% kill rate**,
75 defects against 166 tests, base `5554c79` head `2945551`, run
`fc5fdcb24820a37e`. Method and traps are in `README.md`; raw numbers in
`findings.json`; the runs that produced them in `score-output.log` and
`model-comparison.log`.

## The headline

Rejecting a pair only when every filter rejects it, keeping all 127 kills:

| configuration | excludes |
|---|---|
| `voyage-code-4` both sides | **22.0%** |
| `voyage-4-large` defects, `voyage-code-4` code | 15.4% |
| `voyage-code-3`, description as query and code as document | 14.6% |
| `voyage-code-3`, no `input_type` | 14.2% |
| `voyage-4-large` both sides | 2.1% |

## 1. The free baseline fails outright, and fails the way the code predicted

Asking whether a test's discovery signal touches the defect's own file excludes
77% of pairs — and **skips 80 of the 127 kills**. It is binary, so there is no
threshold to soften: its only operating point loses 63% of the kills.

That is the exact case `defects/reachability.py`'s docstring sets out as the
reason one-hop name overlap cannot prove absence, now measured rather than
argued. The skipped kills are end-to-end tests —
`test_two_runs_over_the_same_input_agree_byte_for_byte` and its siblings — that
drive the pipeline without naming any changed symbol and would still fail on a
defect in `report.py` or `pair_mapping.py`. One hop cannot see the second edge.

Broken into its four signals, only *called names* carries anything: alone it
excludes 80.7% and keeps 42 kills. *Referenced names* keeps 5. *Imported
modules* and *name match* keep none.

**The "own file" signal is structurally inert, not accidentally zero.** The
enumerator runs over `non_test_changes`, so no defect's code refs can name a
test-category file, so a test's own file can never be one of the defect's files.
I verified this on the corpus: the 11 files named by defect code refs are all
`source` or `other`, and none of the 4 test-category files in the change set is
among them.

## 2. The embedding model dominates every other choice

`voyage-code-4` excludes 22.4% on the description filter alone against
`voyage-code-3`'s 10.2% — more than double, on identical texts, identical
thresholding, identical scoring. Nothing else moved the number that far.

The two `voyage-code-3` rows differ only in `input_type` and land 0.4 points
apart. The union rule adds at most 4 points over the best single filter. The
model swap adds 12.

**The code-region filter stays weak everywhere.** Its best is 10.6%
(`voyage-code-3`) and `voyage-code-4` gets only 5.9% from it. Comparing a diff
hunk with a test function is apparently a harder retrieval problem than
comparing a prose description with one, which is the opposite of what the plan
behind this experiment expected.

## 3. Mixing two models costs, and Voyage's compatibility claim does not cover it

The Voyage 4 announcement says "All four models produce compatible embeddings,
meaning embeddings generated from different models can be used interchangeably",
and names `voyage-4-large`, `voyage-4`, `voyage-4-lite`, `voyage-4-nano`. **It
does not name `voyage-code-4`.**

Measured against the live API on 2026-08-30, on identical text:

| pair | cosine on identical text |
|---|---|
| `voyage-4-large` vs `voyage-4` (both named) | 0.93 |
| `voyage-4-large` vs `voyage-4-lite` (both named) | 0.90 |
| `voyage-4-large` vs `voyage-code-4` (not named) | 0.72 prose, **0.56 code** |
| `voyage-4-large` vs `voyage-code-3` (different series) | ~0.00 |

So "interchangeable" is worth about 0.9 in practice, `voyage-code-4` sits well
outside that band, and it diverges worst on code — exactly the content the code
side of the filter handles. The measured cost matches: using `voyage-4-large`
for defect descriptions instead of `voyage-code-4` drops the union from 22.0% to
15.4%.

**Use one model for both sides.** The cross-model cosine carries the gap between
the models as well as the gap between the texts.

## 4. "Best lossless" is a minimum statistic, and it misleads on its own

`voyage-4-large` scores 2.1% — apparently catastrophic. At **one** kill lost its
description filter reaches 27.1%, the best in that column. Its lossless figure
is one unlucky pair, not a bad model.

This is why `compare_models.py` reports zero, one and three kills lost. The
lossless figure is the right bar for *adopting* a filter, because one skipped
kill is the failure #312 exists to remove. It is the wrong bar for *comparing*
models, because it discards everything except the worst case.

`voyage-code-4` leads on both readings — 22.4% at zero kills lost and 46.2% at
three — which is why it is the recommendation rather than `voyage-4-large`.

## 5. What is worth keeping regardless of the decision

**`input_type` matters and the product cannot send it.** For `voyage-code-3`,
marking both sides of the code-to-code comparison as `document` excludes 10.6%
where sending no `input_type` excludes 3.2%. `ModelClient.build_embedding_request`
sends `model` and `input` only, so adopting any of this means changing it —
**which moves the embedding request key and orphans the recorded linking
transcripts**. Worth doing when something needs it, not speculatively.

**`voyage-code-4` and the 4-series models exist and take `input_type` of `query`
or `document`.** I verified this against the live API; a third value returns a
400 naming the two accepted ones.

## 6. What this does not settle

**One review, and the verdicts are our own judge's answers.** Every number here
measures agreement with ourselves on a single Gate 2 run over this repo's own
code. That is the right target for a prefilter — its only job is to avoid
skipping a pair the judge would have called a kill — but it is not evidence
about whether the judge is right.

**The thresholds are fitted to the data they are scored on**, so the exclusion
shares are ceilings rather than operating points. One detail cuts the other way
and is worth checking rather than trusting: `voyage-code-4`'s winning threshold
is **0.018**, which is close to "exclude pairs whose vectors point away from each
other". I believe a near-zero cut is likelier to survive a held-out check than
`voyage-code-3`'s fitted 0.321, because it is a statement about the geometry
rather than a constant tuned on 127 kills. **I have not verified that**, and a
hold-out against #315's archetype labels is what would.

**Cost.** The pair stage is $3.51 of the run's $4.25, of which $2.46 is output.
Removing 22% of pairs removes about 22% of the output and a smaller share of the
input, taking the review to roughly $3.50. That is real but modest next to the
response-encoding change measured separately — see below.

## Recommendation

Do not adopt a prefilter yet, but stop treating it as closed. Specifically:

1. **If a filter is adopted, use `voyage-code-4` on both sides.** Not
   `voyage-code-3`, not a mixed pairing.
2. **Run the hold-out against #315's archetype labels before adopting
   anything.** At 22% the check is now worth its cost; at 14.6% it was not.
3. **Take the response-encoding change first.** Measured on the same 332
   recorded transcripts, the defect id is 42.8% of the stage's output and the
   reason on surviving verdicts is another 30.7%; replacing the id with a short
   index and dropping the reason where `fails` is false cuts output by **72.4%**
   — more than three times what the best filter saves, and it skips no
   judgement at all. It needs its own pilot for accuracy, not for cost.
4. **Deduplicate defects.** 75 defects collapse to 27 distinct kill vectors, and
   seven of them are the same defect stated seven ways. Merging exact duplicates
   alone gives 55 defects, 27% fewer pairs, with no coverage lost — and the
   duplication traces upstream to obligations that state the same requirement,
   which is #210, over-merging, and #242, where one wrong link stops a group of
   duplicate obligations from merging.
