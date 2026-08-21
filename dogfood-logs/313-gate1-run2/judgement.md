# Judgement — #313 Gate 1, run 2

*Run at `03c96e5` on branch `313-defect-enumeration`, 2026-08-21, immediately
after run 1. Byte-identical `current-task.md` — no edit between the two.*

Command, identical to run 1:

```
.venv/bin/acceptance decompose --task current-task.md
```

Exit 1, same single line of output:

```
acceptance: model error: requirement 'task-01' was disposed more than once
```

## Why this run exists

To establish that the run-1 failure **replays** rather than being a one-off
provider draw. It does. The four transcripts run 1 recorded were still on disk,
so this run issued no live call, replayed the stored batch-1 response containing
twelve `task-01` dispositions, and died at the same line.

That is the point worth keeping: the abort is now a property of the recorded
input, not of the model's mood on the day. Any further attempt on this exact
task file will fail the same way until either the tool changes or the transcript
is deleted by hand.

It also distinguishes this case from #298, which reported the same crash as
*intermittent* — #265's run 2 re-issued the byte-identical request live, after
deleting the transcript, and came back clean. That remains plausible here and
was not tried: doing so would be reaching around a defect rather than reporting
it.

No `--continue` was passed, and none could be. Run 1 crashed before writing a
ledger entry, so there is no run id to continue from.

The full diagnosis, the batch-by-batch disposition ids, and the triage are in
`dogfood-logs/313-gate1-run1/judgement.md`. Nothing in this run adds to them
beyond the determinism finding above.
