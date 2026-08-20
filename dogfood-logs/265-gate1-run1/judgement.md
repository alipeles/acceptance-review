# Judgement — #265, Gate 1, run 1

`decompose` over the mandate in `current-task.md` (saved beside this file), on
`main` at `b7929eb`. No `--continue`; this is the first run for this task.

## Outcome: the run aborted. No obligation breakdown was produced.

```
acceptance: model error: requirement 'task-01' was disposed more than once
exit=1
```

Re-running reproduces it byte for byte, because the response is recorded and
replays. So this is not a flaky failure to shrug at — with this task file and
this transcript store, `decompose` cannot complete.

## What the model actually returned

The failing call is the third decomposition batch (`partition: {"size": 8}`),
which was asked about two requirements — `exclusion-06` and `task-01`. It
returned three dispositions:

```
ids: ['exclusion-06', 'task-01', 'task-01']
```

The two `task-01` entries are the same disposition twice. Both are `yielded`,
both carry seven obligations in the same order with the same descriptions and
the same `source_quote`s. They differ in exactly one respect: **every id in the
second copy has `-dup` appended.**

| copy | head obligation | the six in `more_obligations` |
|---|---|---|
| 1 | `share-opening-text-across-run-requests` | `client-marks-reusable-opening-end`, `shared-content-byte-identical`, `shared-content-at-front`, `shared-content-leading-run`, `reordering-preserves-content`, `client-does-not-overmark-opening` |
| 2 | `share-opening-text-across-run-requests-dup` | the same six, each with `-dup` appended |

The `-dup` suffix is in the model's own response, not added by our `_unique`
helper — it is visible in the recorded response body.

## Why it aborts rather than being absorbed

`_filter_dispositions` (`src/acceptance/requirement/obligations.py:1203-1216`)
already anticipates this failure mode. Its comment says so:

> An EXACT repeat of a disposition already returned in this response is dropped,
> not rejected. It carries no information the first copy did not, and a response
> that repeats itself verbatim is a degenerate generation rather than a
> contradiction — observed once the obligations moved inside the dispositions and
> responses grew: the model emitted its whole disposition list twice.

That is exactly what happened here. But the guard tests `previous == entry`,
byte equality of the whole disposition object, and the `-dup` ids break it. So
the copy is passed through as a *differing* duplicate, and `_requirement_map`
(`obligations.py:1265-1269`) raises `SchemaValidationError`, which the CLI
reports as a model error and the run ends. No report, no obligations, no verdict
— for any of the eighteen requirements, not just `task-01`.

## Triage

**Tool defect, not a fair finding about the mandate.** Two reasons:

1. The first copy is a complete, well-formed answer. The information needed to
   proceed was returned; the review was abandoned because the model said it
   twice.
2. The disposition the code applies is documented as being for a
   *self-contradiction* (#217, `M1.2.r2` — "two different answers for one
   requirement"). Two answers that are identical apart from a mechanical `-dup`
   suffix on every id are not two different answers. They are one answer,
   repeated, exactly as the guard three functions earlier describes.

This is the same family as **#248**, which is closed: there the model echoed a
single obligation into `more_obligations` and `_unique` suffixed the second id
with `-2`; the fix reads `more_obligations` as the rest of the list and collapses
an echoed head. That fix operates one level below this one. #248 collapses a
repeated **obligation** inside one disposition; nothing collapses a repeated
**disposition** inside one response unless it is byte-identical.

Queued as a filing in `docs/DEFERRED.md`, drafted as a sub-issue of **#181**
(decomposition). Not filed — it goes to the human at the gate.

## What was done next

The task file was **not** rewritten in response to this. Rewording to dodge a
degenerate generation would be tuning the input around a tool defect, and would
also destroy the evidence that it happens.

Instead the orphaned transcript for this one call was deleted from
`.acceptance/cache/transcripts/` and the identical request re-issued live, to
establish whether the repeat reproduces on the same input. That is run 2.

## Severity note

This is worse than an inaccurate obligation, because it is not a finding that
can be read and judged — it is the absence of any output at all. On a task file
that triggers it, Gate 1 cannot be reached by any amount of care in the mandate.
