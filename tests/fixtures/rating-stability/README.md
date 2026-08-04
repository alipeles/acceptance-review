# Rating-stability corpus

Captured dogfood iterations, kept as **test data for fixing the instability they
document** (#180). Not currently read by any test — it is the evidence a fix has
to be measured against, recorded while the judgements were still fresh.

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

Ratings moved in both directions, and the corpus separates three distinct causes.
A fix must handle all three, and must not collapse them:

1. **Real gaps the tool found correctly.** `fixed-command-surface` (run 1) and
   `default-to-most-recent-review` (run 2) were genuine — the second caught a
   test that did not verify its own name. The tool earned these. **A fix that
   stabilises ratings by making the judge less sensitive would lose them.**
2. **False negatives.** Run 1 rated `default-to-most-recent-review` STRONG on
   the evidence run 2 correctly called `nominal`. Instability is not only noise
   around a true value; at least one run was simply wrong.
3. **Movement with no change in evidence.** `remove-stale-next-instruction-file`
   fell STRONG → partial in run 3 while neither the behaviour nor its test
   changed — only *other* tests in the same file did. `no-speculative-writing`
   fell in the very run that added a test supporting it.

The cleanest reproduction is run 2 → run 3: the diff is one test file, the
stale-removal test within it is untouched, and its obligation still moves.

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
