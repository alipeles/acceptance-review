# Rating-stability corpus

Captured dogfood iterations, kept as **test data for fixing the instability they
document** (#180, umbrella #183) — the evidence a fix has to be measured
against, recorded while the judgements were still fresh.

## What is read by a test, and what is not (#190)

Every run here now backs a regression case in `tests/fixtures/rating-regression/`,
scored by `tests/benchmark/test_rating_regression.py`. A case reads two files
from its run:

| file | read? | by what |
|---|---|---|
| `current-task.md` | **yes** — verbatim, as the case's task input | `benchmark/corpus.py` |
| `revisions.txt` | **yes**, indirectly — each case pins the same head SHA, plus the base this file does not record | `tests/fixtures/rating-regression/*/case.json` |
| `judgement.md` | **no, not mechanically.** Its conclusions were transcribed into `labels.json` by hand; each case's `case.json` names the judgement it came from, and for runs 3 and 5 which of the two preserved readings is ground truth | — |
| `check-output.log` | **no.** Obligation text and candidate tests were transcribed from it once, when the labels were built | — |

So the judgements are asserted, but the corpus files that carry them are still
prose a human wrote and a human transcribed. **A finding recorded here does not
reach the suite until someone adds it to a `labels.json`.**

The cases are pinned to real commits in this repository rather than to copies of
the source, so a rewritten history breaks them by name rather than shrinking the
suite silently.

**The reasoning lives in `docs/DR-180-evidence-judgement-instability.md`**; this
README covers the layout and how to read the runs. The DR owns the analysis — the
asymmetry, the M5.2 localization, and the constraint on any fix — so the two do
not drift.

## Why it is checked in

`dogfood-logs/` is gitignored and `current-task.md` is overwritten by the next
task, so within a day none of this is recoverable. The expensive part is not the
logs — it is the **judgement** files: whether each finding was a real gap or a
tool defect. That determination cost a full re-run each to establish and cannot
be reconstructed from the output alone.

## Layout

```
<issue>-gate2-run<n>/
  current-task.md     the exact task file the run was given
  check-output.log    the full §16 report it produced
  judgement.md        what was flagged, my disposition, and what happened next
revisions.txt         the commit each run judged
```

## The headline

Three consecutive `acceptance check` runs over **the same task file**, on a
strictly growing test suite, disagreed about **8 of 12 obligations**:

| run 1 | run 2 | run 3 | obligation |
|---|---|---|---|
| STRONG | nominal | STRONG | `default-to-most-recent-review` |
| STRONG | STRONG | partial | `no-speculative-writing` |
| nominal | STRONG | STRONG | `fixed-command-surface` |
| STRONG | partial | partial | `spec-no-longer-describes-written-file` |
| STRONG | partial | STRONG | `byte-identical-retrievals` |
| STRONG | STRONG | partial | `remove-stale-next-instruction-file` |
| UNSUP | STRONG | STRONG | `replace-written-file-with-command` |
| STRONG | partial | STRONG | `retrieve-from-stored-review-state` |

Only 4 of 12 held the same rating throughout.

## How to read it

Ratings moved in both directions, but the corpus's central finding is that the
movement is **not symmetric noise**:

> **In 7 of the 8 unstable obligations, the LOW rating was the correct one.**

Every case where a rating fell turned out to be the judge finally noticing a hole
that had been there all along — including a `--json` code path that deleted a
file in the user's repo and reported nothing. The `strongly supported` ratings
are the unreliable ones. The tool errs toward "looks fine", which is far more
dangerous than noise and is the opposite of what the churn suggests at a glance.

This matters for how a fix is judged. The tempting reading — "ratings bounce
around, damp them down" — is backwards. Three distinct causes, which a fix must
not collapse:

1. **Real gaps, correctly found, on both the up and down moves.** `fixed-command-surface`
   (run 1), `default-to-most-recent-review` (run 2), and all three of run 3's.
   The second caught a test that stored a single review while claiming to verify
   "the most recent" — a test that did not verify its own name. **A fix that
   stabilises ratings by making the judge less sensitive would lose every one of
   these.**
2. **False negatives, which are the real defect.** Run 1 rated
   `default-to-most-recent-review` STRONG on the evidence run 2 correctly called
   `nominal`; runs 1 and 2 both rated `remove-stale-next-instruction-file` STRONG
   while a silent deletion sat in the code. The bug is not that ratings move — it
   is that STRONG is issued when it has not been earned.
3. **Possible genuine noise.** Only `byte-identical-retrievals` survives as a
   candidate, and given the record above it should be treated as unsettled
   rather than as an established example.

### The trap this corpus exists to record

Each run's `judgement.md` holds what I concluded *at the time*, including where I
was wrong. Run 3's was rewritten: I first dismissed all three findings as noise,
reasoning that the diff was purely additive and added tests cannot weaken
evidence. Both premises are true; **the conclusion does not follow**, and acting
on it would have shipped the silent deletion. That inference is the thing most
likely to be repeated by whoever picks this up.

## Caveats

- These are **not** recorded transcripts, deliberately. A transcript embeds the
  full request, so committing dogfood transcripts would put this repo's own
  diffs and task text into test fixtures (`tests/support.py`). These are rendered
  reports only.
- Runs 2 and 3 were **incremental re-runs** (M7.5) building on the prior stored
  review; run 1 of each issue was a first review. A fix must account for the
  carry-forward path, not just the fresh one.
- The `163-gate2-run1` entry is a clean single run, included as a control. One
  clean run is not evidence of stability.
