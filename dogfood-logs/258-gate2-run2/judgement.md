# Judgement — #258 Gate 2, run 2

**BLOCKED again. No report was produced, so Gate 2 still cannot be assessed —
not clean, not unclean, unknown.** This is the second time in a row, against a
tool that was fixed in between.

```
acceptance: model error: no recommendation for 1 of 13 weak obligation(s): no-root-task-file-read
```

Run at base `9def9e7` → head `907779a`, `--mode record`; re-run `--mode replay`
reproduces the identical message. Run 1's abort was *2* of 13; #266 landed to fix
exactly that; this run's abort is *1* of 13, on a **different** obligation.

## #266 did work — it just did not close the failure mode

#266 moved the *"is a test owed here at all"* judgement out of the
recommendation stage and up to decomposition (`RequiredEvidence`), and made
silence at the recommendation stage the only thing that stage has to reject.

The two obligations that destroyed run 1 —
`region-coverage-case-list-omits-missing-path` and
`no-failures-without-root-task-file` — **were both answered this time.** That is
the fix working. What survives is a different thing wearing the same clothes: the
model omitted one criterion out of thirteen, and the stage converts that omission
into a total loss of the review.

## What the transcript shows

Transcript
`.acceptance/cache/transcripts/adf65d6a…f993ed.json`, a single call (this stage
does not partition):

- **13 criteria supplied, 12 returned.** The skipped one is at **position 4** of
  13 — not the tail.
- `stop_reason: "stop"`, 2,901 completion tokens, no `max_tokens`. **Not
  truncation**, and not the DR-164 call-size shed: positions 5–13 all came back.

Two features distinguish the skipped criterion, and only one of them is
discriminating:

| | criterion | class | defects listed | answered |
|---|---|---|---|---|
| 3 | `no-root-task-file-read-check` — *"A check asserts that no test reads the task file at the repository root"* | partially_supported | 1 | yes |
| **4** | **`no-root-task-file-read`** — *"Test execution does not access the repository-root task file"* | **unsupported** | **0** | **no** |
| 12 | `no-failures-without-root-task-file` | unsupported | 0 | yes |
| 13 | `no-root-task-file-dependence` | unsupported | 0 | yes |

So *"criteria with no surviving-defect list get dropped"* is **not** the
explanation: three criteria had none and two of them were answered. What is
peculiar to position 4 is that it is a **near-duplicate of position 3**, which
the model had just answered — the Constraint and its Completion twin, arriving
adjacently, describing the same property from two sides. The most economical
reading is that the model treated the pair as one question and answered it once.
That is a hypothesis from one run, not a demonstrated cause.

## The disposition is the defect, whatever the cause

Even granting that the model should have answered all thirteen, the stage's
response to one missing item is to raise and produce **nothing** — no report, no
verdict, no findings for the other twelve obligations, no record that a
recommendation was owed and not obtained. A single model omission out of thirteen
costs the entire review, and there is no retry anywhere on the path.

This sits badly against a standing invariant: *uncertainty is first-class —
`Indeterminate` and open-question outputs are valid, expected results.* A
recommendation the model declined to produce is precisely an indeterminate
result about **one** obligation. Recording it as such — an unusable answer, or an
`Indeterminate` finding reading *"no recommendation was produced for this
obligation"* — would keep the review, keep the gate red for an honest reason, and
lose only the one prescription. Aborting loses twelve good ones as well.

`_weak_obligations`' docstring argues silence has "no correct reason" now that
`required_evidence` is decided upstream. That is a sound argument about what the
model *ought* to do, and an unsound basis for what the stage should do when it
doesn't.

## Disposition

**Tool defect.** Nothing in `#258`'s own change is implicated: it touches
`tests/` only, and the abort is in `coverage/recommendations.py`. Queued as a
filing (`docs/DEFERRED.md`) — a child of #185 for the abort-vs-`Indeterminate`
disposition, and the near-duplicate-pair observation recorded against #245, which
already owns the Constraint/Completion twin split.

**#258 remains unassessable at Gate 2 and stays unmerged.** The judgement about
its other twelve weak obligations — every one of which is `partially_supported`
or `unsupported`, so the report would very likely have been unclean anyway — has
still never been made.

## Second finding, visible even without a report

`no-root-task-file-read` came back **`unsupported`** — no mapped test — while its
Completion twin `no-root-task-file-read-check` came back `partially_supported`.
`tests/test_root_task_file_is_not_read.py` exists and is exactly that test. A
`(no mapped test)` on an obligation whose twin is supported is the #245 split, as
`session-state/258.md` anticipated. Recorded, not acted on.
