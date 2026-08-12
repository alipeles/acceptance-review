# Judgement — #258 Gate 1, run 1

Base SHA: `3aeb676`. Command:

```
.venv/bin/acceptance decompose --task current-task.md --mode record
```

## Result

22 requirements → 21 obligations, strictly 1:1. One requirement
(`completion-01`, the bare `Implementation` marker) yielded no obligation,
correctly labelled *deliberately none*. **No open questions, no unreconciled
cluster, no composites, no spurious links.**

Every obligation is a faithful restatement of its requirement. Checked
one by one against the source text; no quantifier drift, no added or dropped
bound, no requirement represented by another requirement's content.

## Findings

### 1. A redundancy in the input, not in the tool — fixed, gate re-armed

`constraint-09` and `completion-06` have identical truth conditions:

| requirement | text |
|---|---|
| `constraint-09` | A test run reports no failures when no task file is present at the repository root. |
| `completion-06` | The suite passes when no task file is present at the repository root. |

Both were derived faithfully, producing two obligations for one requirement.
The fault is the task file's: the house style makes a Completion expectation the
*evidence* form of a Constraint (`A test asserts that …`), and `completion-06`
was written as a restatement instead. Linking left them separate, which is
defensible — it merges on identical truth conditions and these are worded as
different subjects (a test run vs the suite).

**Disposition: the sanctioned rewrite of weak wording.** `completion-06` was
deleted; `constraint-09` already carries the requirement. Re-run as
`258-gate1-run2`.

### 2. Scope-exclusion typing — evidence for #205, queued

All five scope exclusions were typed `human_review`. In run 2, over five
byte-identical exclusion requirements, they came back `compatibility` ×1 and
`functional` ×4 — no overlap with run 1's typing at all.

Checked the consequence rather than assuming one: the type is consumed
structurally in exactly one place (`requirement/linking.py:171`, which keys on
`TEST_DEMAND`), so neither typing changes any downstream behavior here. It is
not a `human_review` pause and does not gate anything. The significance is only
that the type carries no reliable information, which is #205's subject.

**Disposition: tool defect, queued as a comment on #205.** Not addressed here.

### 3. An id collision suffix, noted not filed

`constraint-07` yielded `region-coverage-case-list-non-empty-2`, suffixed
because `completion-03` took the unsuffixed id. Stable across both runs. The two
obligations correctly stayed separate — one is the behavior, one is the demand
for a test of it — so the suffix is an id-generation artifact with no effect on
the breakdown. Recorded here rather than queued.

## Verdict

The decomposition is accurate and I would defend it. The one correction was to
the input, and the gate was re-armed by re-running.
