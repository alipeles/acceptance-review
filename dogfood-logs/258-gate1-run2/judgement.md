# Judgement — #258 Gate 1, run 2

Base SHA: `3aeb676`. Command:

```
.venv/bin/acceptance decompose --task current-task.md --mode record
```

Run 2 of 2. Run 1 (`dogfood-logs/258-gate1-run1/`) was accurate, and the rewrite
that produced this run removed a redundancy in the *task file* — `completion-06`
restated `constraint-09` — not a tool finding.

## Result

21 requirements → 20 obligations, strictly 1:1. `completion-01` (the bare
`Implementation` marker) yielded no obligation, correctly labelled *deliberately
none*. **No open questions, no unreconciled cluster, no composites, no spurious
links, no duplicate obligations.**

## Accuracy check

Each obligation against its requirement. All 20 are faithful restatements:

- Bounds preserved in direction. `constraint-06` ("built **only** from the
  committed task files") keeps the exclusive bound; `constraint-08` ("**omits** a
  path that is not present") keeps the omission rather than widening it to a
  general filter.
- Nothing invented. No obligation states a requirement absent from the mandate.
- Nothing lost. Every one of the 21 requirements is represented, or explicitly
  and correctly not.
- `task-01` retains its subordinate clause this time ("which is a scratch input
  rewritten for every task"). Run 1 dropped it. Both readings are acceptable —
  the clause is context, not an obligation — and nothing downstream turns on it.

## Triage of open questions

**None raised.** Nothing to triage under any of the three cases.

As in #191's Gate 1, zero open questions is **observed, not confirmed**: #193
holds that membership oscillates, and a re-run in replay mode would replay by
construction and prove nothing. Distinguishing a genuinely question-free
decomposition from a lucky draw needs #189's harness with determinism off.
Recorded as unresolved, not as a clean signal.

## Findings

One, carried from run 1 and unchanged: **scope-exclusion typing is unstable**.
The five exclusion requirements are byte-identical between the two runs and were
typed `human_review` ×5 in run 1, then `compatibility` ×1 + `functional` ×4
here. Consumed structurally in one place only
(`requirement/linking.py:171`, keyed on `TEST_DEMAND`), so it changes no
downstream behavior — the defect is that the type carries no reliable
information. Queued as a comment on #205.

## Verdict

**Gate 1 passes at `3aeb676`.** The breakdown is accurate and I would defend it;
no open questions to triage; the one negative finding is attributed to a tool
defect with a drafted filing in the queue.
