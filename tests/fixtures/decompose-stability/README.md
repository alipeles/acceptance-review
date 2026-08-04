# Decompose-stability corpus

Captured `decompose` iterations, kept as **test data for measuring and fixing the
instability they document** (#189, umbrella #181/#184). Not yet read by any test.

Sibling of `tests/fixtures/rating-stability/`, which does the same job for the
**evidence-judgement** stage (#180). Kept separate deliberately: that corpus shows
variance in `would_be_caught` over a byte-identical mapped test set; this one
shows variance in the **obligation set and open questions** produced from a task
file. Different stage, different failure, and #189 must measure both.

## The distinction that governs what counts as a defect

Not every difference between two runs is the same kind of problem, and a corpus
that blurs them will drive the wrong fix:

- A **content difference** is a requirement, open question or judgement present in
  one run and absent in another. Something was lost. This is a **quality** defect
  in the judge and has to be fixed on its own terms — a determinism layer that
  pinned the output would simply freeze the loss in place.
- A **shape difference** is the same content partitioned differently — three
  obligations in one run where another produced one. Nothing was lost. This is
  what a **determinism layer** exists to pin down, and it must not be counted
  against decomposition quality.

Both appear in this corpus, and separating them is the first thing to do with any
new observation. #189 reports the two as separate figures for this reason.

## The caveat that governs how this is read

> **The task file is NOT byte-identical across these runs.** Every run was given
> an edited file.

This is the sharpest difference from the rating-stability corpus, and mistaking
one for the other would produce a wrong conclusion. Nothing here is evidence of
**resample variance** (the same request drawn twice). It is evidence of
**perturbation sensitivity** — how far a judgement moves under a change to the
request that is irrelevant to it. `task-diffs.txt` holds the exact edit between
each pair of runs, which is what makes the irrelevance claim checkable rather
than asserted.

A resample corpus for this stage does not exist yet and cannot be produced by
hand: it needs N draws over one unchanged file, which is #189's harness.

## Layout

```
189-gate1-run<n>/
  current-task.md        the exact task file the run was given
  decompose-output.log   the obligations and open questions it produced
  judgement.md           what I concluded about that run, at the time
task-diffs.txt           the exact edit between consecutive runs
```

Runs 1 and 2 were reconstructed from the session transcript after the fact, since
`current-task.md` is overwritten by each edit; the reconstruction was verified by
diffing run 2 against run 3's on-disk copy and confirming the diff is exactly the
single edit that was made. Runs 3, 4 and 5 are unmodified on-disk snapshots.

Run 4 additionally carries a `prediction.md`, written **before** the run. Run 2's
judgement noted that a reconstructed expectation is worth less than a recorded
one, so run 4 pre-registered its expected outcome; two of its four predictions
were wrong, which is the point of recording them. Later rounds should keep doing
this.

## The headline

Seven consecutive `decompose --mode record` runs during Gate 1 for #189:

| run | obligations | open questions |
|---|---|---|
| 1 | 24 | 5 |
| 2 | 18 | 3 |
| 3 | 20 | **0** |
| 4 | 20 | **0** |
| 5 | 24 | 2 |
| 6 | 25 | 4 |
| 7 | 33 | 1 |

**The load-bearing observation is that open-question membership oscillates.**

| question | run 1 | run 2 | run 3 | run 4 | run 5 | run 6 | run 7 |
|---|---|---|---|---|---|---|---|
| output format | **present** | **present** | absent | absent | **present** | **present** | absent |

**The task file never says anything about output format**, in any of the seven
versions. The text that would answer the question is absent throughout, and the
question's presence oscillates anyway. A question that returns was never
resolved — it was dropped.

An open question is a first-class output of this tool ("uncertainty is
first-class"). Dropping one is the tool silently converting *I don't know* into
*nothing to see* — the precise failure this product exists to detect in others,
and worse than an unstable evidence rating, which at least renders something a
reader can dispute.

**A third, cleanest content difference** (run 7): the scope exclusion *"interpreting
the figures it produces, setting a threshold a rating must meet, or reducing the
variance it finds"* produced **one** obligation in run 5, **zero** in run 6, and
**three** in run 7 — with that section of the task file unchanged across all
three. Run 6's judgement originally called the breakdown accurate; the correction
is preserved in place, above the original wording.

Two further findings, each recorded in the run judgement that produced it:

- **A requirement lost half its content** (run 4). A compound bullet — *"which
  obligations appear in some runs but not others, **and which open questions
  do**"* — produced an obligation with the open-questions half missing. Fixed at
  source by splitting the bullet; run 5 extracts both.
- **Obligation text and type degrade on byte-identical input** (runs 4–7). The
  same constraint text produced an obligation naming
  `benchmark/scoring.py::disclose_variance` in run 3 and one that dropped the
  symbol in run 4. Separately, `record-run-provenance` was typed `invariant`
  (runs 3–4) → `docs_config` (run 5) → `functional` (run 7) on unchanged text.
- **Prohibitions are typed `human_review`** (run 7). Three obligations forbidding
  the harness from setting thresholds or reducing variance — all statically
  checkable — were typed as needing human review, which is a mandatory Gate 2
  pause. As typed they would block a clean Gate 2 by construction, forever. Both
  this and the type churn above are live inputs to **#162 Part 2**, which proposes
  keying human escalation on obligation type: the axis produces false positives as
  well as being unstable.

**A stable obligation count can conceal a re-split.** Runs 3 and 4 both produced
20, but run 3's single `harness-runs-review-pipeline-repeatedly` is three
obligations in run 4, from an unchanged sentence. Any variance metric #189
produces must compare **aligned obligation sets, never counts**.

## How to read it

Several of the changes across these runs were **correct responses to a genuinely
improved task file**, and must not be counted as instability:

- Run 1 → 2 collapsed ~8 duplicate obligation pairs, because the run-1 task file
  stated the same requirement in the prose, in Constraints **and** in Completion
  expectations. The duplication was real and the merge was right. (The tool-side
  issue is #144, still unimplemented — there is no dedup filter in
  `src/acceptance/requirement/`.)
- Run 2 → 3 dropped a `human_review` obligation type, because the vague bullet
  that earned it was replaced with a checkable one. Also right.

- Run 4 → 5 extracted both halves of a requirement that run 4 had truncated,
  because the compound bullet was split in two. Also right.

What is **not** explained by the task file improving: the two open questions
vanishing in run 3 and returning in run 5; the obligation count rising 18 → 20 on
an edit that added one bullet; the re-split of an unchanged sentence between runs
3 and 4; and the symbol and type degradation on byte-identical text.

### The trap

The tempting reading at run 3 was *"this is clean, so Gate 1 passed and the
earlier runs were just a bad task file."* The task file genuinely was bad — but
run 3's clean sheet was reached partly by an unexplained drop of two open
questions, and run 5 proved it by bringing both back. **A clean run reached
because questions vanished is not the same as one reached because they were
answered, and only the history distinguishes them.**

Run 4's judgement shows the error being made in real time: it scored the
zero-question result as *leaning toward the questions having been genuinely
resolved*. Run 5 falsified that. Resolution is not a state a question can return
from. This mirrors the inference recorded in
`docs/DR-180-evidence-judgement-instability.md` — check the finding on its merits
first, attribute to instability only after.

## Caveats

- These are **rendered CLI outputs, not transcripts** — deliberately, for the
  reason given in the rating-stability README: a transcript embeds the full
  request, which would put this repo's own task text into test fixtures.
- Five runs is not a rate. It is a set of observations, recorded because the
  judgements are expensive to reconstruct and worthless a day later. The
  oscillation table is strong qualitative evidence and still not a frequency.
- All five runs used the default model and `--mode record`. Nothing here says
  anything about cross-model variance; that is the third axis #189 must add.
- Gate 1 for #189 passed at **run 5**, not run 3.
