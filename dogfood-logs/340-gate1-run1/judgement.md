# #340, Gate 1, run 1 — aborted on a provider schema error

The run never produced a decomposition. It died on an unhandled
`litellm.BadRequestError` in the `decompose-summary` span stage:

```
Invalid schema for response_format '_Decomposition': In
context=('properties','open_questions','items','properties','source_quote'),
" is not allowed in string literals for structured outputs (strict=true).
```

## Cause — a tool defect, verified

`source_quote` is constrained to an enum of the answering requirement's own
spans (`requirement/obligations.py:835`, and `:1117` for the span stage, which
constrains to a single span and so emits `const` rather than `enum`). The task
file's first paragraph contained a quoted phrase. The quote character reaches
the generated JSON Schema intact, and OpenAI's strict structured-output mode
refuses it.

I verified the schema half with no model call:

```
constrain(_Decomposition, {"source_quote": ['comes back "this test would not
catch it" nearly every time.']})
```

emits `{"const": "comes back \"this test would not catch it\" nearly every
time."}` for both `_DecomposedObligation` and `_OpenQuestion`.

Not a tool defect I can date. `dogfood-logs/232-gate1-run1/`, 2026-08-10, ran a
task file whose line 4 carries the same construction and succeeded. What changed
since is unmeasured; the model has moved.

## Disposition

Attributed to the tool and drafted as a filing in `docs/DEFERRED.md`
(2026-09-18, blocker, sub-issue of #181 — the decomposition umbrella). The fix
is in the decomposition stage's request assembly, which this task's Scope
exclusions place outside it.

To get past it I reworded the one sentence to drop the quotation marks. That is a
workaround, recorded here rather than silent: the defect is queued, and the
rewording changes only my own prose, not what the software must do.

## The log

`output.log` is absent. The run was first captured with `> output.log 2>&1` and
produced a zero-byte file — the empty-log problem `CLAUDE.md` records. The
traceback above was recovered by re-running without the redirect and is
reproduced here in full, because that is the run's only durable record.
