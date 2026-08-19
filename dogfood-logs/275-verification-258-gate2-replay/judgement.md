# Judgement — #275 verified against the run that produced it

Not a gate run. This is #275's fix executed over **#258's Gate 2 run 2** — the
run this issue was filed from — with the model responses held fixed.

## Why it is a controlled comparison

- Same revisions: base `9def9e7`, head `907779a`.
- Same task file, byte-identical to
  `dogfood-logs/258-gate2-run2/current-task.md` on `258-committed-task-file-corpus`.
- Same model responses: run in `--mode replay` against that run's own 27 recorded
  transcripts, copied into a detached worktree at `907779a`. **Every request hit
  cache** — the run made no live call, so the recommendation stage received the
  exact bytes that aborted it before.
- The tool binary is #275's branch (`.venv/bin/acceptance` from the
  `275-recommendation-omission` worktree), so the only variable is the fix.

The transcript keys still match, which is itself worth recording: #275 changed
no prompt, no response schema and no supplied-id set, so the recommendation
stage's request key did not move.

## Before

```
acceptance: model error: no recommendation for 1 of 13 weak obligation(s): no-root-task-file-read
```

No report, no verdict, no findings — twelve honoured prescriptions discarded with
the run.

## After

```
Task completion: INCOMPLETE

12 obligation(s) with non-discriminating test evidence (...)
```

A full report over 20 obligations. The omitted criterion is obligation 5:

```
  5. No test reads the task file at the repository root.
       requirements: constraint-01
       code evidence: addressed
         5.1  tests/test_root_task_file_is_not_read.py#@@ -0,0 +1,95 @@
         5.2  tests/requirement/test_task_file.py#@@ -89,14 +94,21 @@
         5.3  tests/requirement/test_region_coverage.py#@@ -43,11 +44,13 @@
       test evidence: indeterminate  [tier: static]
         (no mapped test)
         recommended test: NOT OBTAINED — no prescription was produced
           why: the recommendation stage was given 13 criteria and returned 12;
                no prescription was produced for this one
```

Every part of the Acceptance is visible in one block on the real case:

- the review exists, where before there was none;
- the omission is an explicit record, not an absence, and it names the arithmetic
  (13 asked, 12 returned) that the original error message reported before
  discarding everything;
- it is `indeterminate` on the evidence axis, so it is not counted among the 12
  obligations rated as having non-discriminating evidence — the review does not
  claim to have judged it;
- the verdict is INCOMPLETE, so the gate stays red;
- **13 `recommended test:` lines**, of which exactly one is NOT OBTAINED. The
  twelve prescriptions that were being thrown away are all present.

## What this does not settle

#258's Gate 2 is **not clean** — INCOMPLETE, with 10 obligations `partially
supported`, 2 `unsupported`, and this one `indeterminate`. That is #258's work to
triage, and this run is not a substitute for its own session re-running the gate
against a current head (its branch tip is now `7c2c3d7`, one commit further on).
What is settled is that the gate can be *assessed* at all, which it could not be
before.

The `indeterminate` obligation will keep #258's gate red until its prescription
is obtained. That is the honest outcome and the argument for the queued re-ask
decision — a single re-ask over the missing id would most likely have produced
it.
