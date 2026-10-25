# #414 Gate 1 run 6 — accurate, no open questions

Run `b4a84b5d7ad8a84c`, `--continue 3ae1a86e857c8a45` (Gate 2 run 1). Re-armed
by two task-file changes after Gate 2 run 1:

- task-04 (now task-03) says "its calls to Claude models" instead of "its model
  calls": the Message Batches API carries Claude completions only, and Gate 2
  run 1's findings on obligations 6 and 8 were right that the old wording
  promised more.
- The pair-stage requirement is removed. #385 (merged as bbda8a0) replaced the
  batched pair judge it named; the cache reads it asked for were shown in Gate 2
  run 1 (14.9%) before the stage went.

16 obligations over 8 requirements, 0 open questions. I believe the breakdown is
accurate: nothing invented, nothing missing. task-03 now splits into five
(opt-in, held in the run configuration, off by default, `check` and `decompose`
direct, scripts can switch it on). `batch-api-opt-in-off-by-default` and
`check-decompose-call-model-directly` overlap, but they make different claims:
one about any run's default, one about two commands.

**Nothing was carried, correctly.** "7 derived, 0 carried, 1 revised", $0.46.
#310's merge (13dcf9c) rewrote the decomposition system prompt, which is part
of every carry key, so every requirement had to be derived again. Not a tool
defect; nothing filed. Obligation ids moved as a result (for example
`min-reusable-prefix-per-model` is now `min-reusable-prefix-512-tokens`).
