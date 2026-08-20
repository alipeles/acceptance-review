# Judgement — #264 Gate 2, run 1

**Command:** `.venv/bin/acceptance check --task current-task.md --base c652ab4 --head f506a76 --mode record`
**Run id:** `dec26e67f2fc2fc0`
**Verdict:** `INCOMPLETE` — **not clean.**

## What it found

Every one of the 28 obligations was **addressed** on code evidence, and 27 of 28
requirements yielded obligations (the 28th, `[completion-01] Implementation`, was
deliberately declined as a section marker). No open questions. No unrequested
changes.

Three obligations had **`unsupported`** test evidence — meaning no test was
mapped to them at all:

| obligation | recommended test |
|---|---|
| `cli-surfaces-breakdown` | CLI output includes the breakdown of tokens, cost and cached share by stage |
| `breakdown-absent-from-review-state` | Review state output contains no stage-by-stage breakdown data |
| `breakdown-absent-from-rendered-report` | Rendered report output contains no stage-by-stage breakdown data |

## Disposition: all three were real, and all three were addressed

**No tool defect here.** The recommendations were exactly right and the gap was
mine. The first commit asserted three things by writing them in comments and
never testing them:

- nothing exercised the CLI footer end to end — `_report_usage` was called by
  `main`, but no test ran `main` and looked at the output;
- nothing asserted that the breakdown stays out of the persisted review;
- nothing asserted that it stays out of the rendered §16 report.

The last two are the load-bearing ones: they are what protects the
byte-identical-rerun invariant (M0.5), and "I put it on stderr, so it cannot
reach review state" is reasoning, not evidence.

Fixed in `23cf2e7` with five tests, including one that varies token usage between
two otherwise identical runs and demands identical review state and report — the
property the two absence tests exist to protect, exercised directly rather than
by spelling. The absence checks also assert that their own marker list trips on a
real rendered breakdown, so they cannot pass by failing to detect anything.

Re-run: `dogfood-logs/264-gate2-run2/`.

## What the run demonstrated about the delivery itself

The footer is the deliverable and it worked, across seven stages:

```
  this run spent $0.1621 on 18 live call(s); the evidence cost $0.1857 to record
  (6 call(s) replayed at no cost to this run)
```

Both halves of the issue's trap are visible in one table: `decompose` shows
`$0.0000` this-run against `$0.0223` recorded (fully replayed), while
`test-to-obligation mapping` shows `$0.0969` on both (fully live). And the
`cached` column separates `—` (transcripts recorded before the cache fields
existed — unmeasured) from `0.0%` (measured, nothing cached).

One incidental finding worth keeping: **mapping is 60% of the cost of a check**
($0.0969 of $0.1621, 14 calls, 69k prompt tokens, 0% cached). That is the first
time this has been measurable, and it is the number #265 exists to move.
