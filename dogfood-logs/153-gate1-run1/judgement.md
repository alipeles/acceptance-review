# Judgement — #153 Gate 1, run 1

Run: `acceptance decompose --task current-task.md --mode record`, at `4b78d62`,
in the `153-scope-exclusion-obligations` worktree. `output.log` is the replay of
the same recording; two consecutive replays are byte-identical.

## Shape

26 requirements → 18 obligations, 8 deliberately none.

| Section | Requirements | Obligations | Declined |
|---|---|---|---|
| Task | 1 | 1 | 0 |
| Constraints | 11 | 11 | 0 |
| Scope exclusions | 7 | 0 | 7 |
| Completion expectations | 7 | 6 | 1 (`Implementation`, a bare section marker) |

Every constraint is accounted for, none invented, none dropped. **Zero open
questions** — worth recording given #193's oscillation on unchanged input.

## Real findings

**1. All 7 scope exclusions declined uniformly — correct behaviour today, and
exactly the defect this task exists to remove.** Not a tool defect: #235
deliberately made exclusions decline, and the sibling-consistency rule from
#219/#230 is visibly holding (7 of 7, same disposition, none inverted into a
requirement of the change). It is self-demonstrating: this task file's own
exclusions are invisible to the review that judges this task. No action; the
task is the action.

Consequence to carry to Gate 2: once this ships, these same 7 bullets *will*
yield obligations, so the Gate 2 run over this task file should show 25
obligations, not 18, with 7 on the code-evidence-only axis.

**2. `constraint-03` is typed `test_demand`, and the type is inverted.** The
requirement is *"No test is recommended for an obligation that admits code
evidence only."* Its demand is the **absence** of a test recommendation, not the
presence of a test. `test_demand` means the obligation's demand *is* the test
(DR-232), so a downstream stage looking for a test to satisfy it would be
satisfied by precisely the evidence the requirement forbids.

This is the same failure shape #232 fought — the word "test" appearing in the
text pulling the type toward `test_demand` — surviving in the inverse case,
which #232's corpus did not cover. `functional` or `invariant` is right.

Disposition: **tool defect**, queued as a filing (comment on #205, evidence for
assigning types in a separate pass). Type assignment is a scope exclusion of
this task (#205), so it is not fixed here.

## Not findings

- `task-01` yields an obligation overlapping `constraint-01`/`-02`/`-05`. The
  Task line is a summary of the constraints, so some overlap is expected;
  granularity is excluded from this task (#117). Noted, not filed.
- `constraint-09` typed `explanation_observability` — reasonable for "a reader
  of the report can tell X from Y".
