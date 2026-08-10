# Judgement — #144 Gate 1, run 1

Run at `9724df4` (branch `144-merge-duplicate-obligations`), `decompose` recorded
then replayed. 29 requirements, 28 with obligations, 1 deliberately none,
**30 obligations**.

## Accuracy — confirmed

**No invented obligations.** Every one of the 30 traces to text in the task file.

**None of the real obligations missing.** All 12 Constraints, all 5 Scope
exclusions and 8 of 9 Completion expectations carry an obligation. The ninth,
`[completion-01] Implementation`, is declined with *"a section marker naming the
deliverable, with no checkable requirement content"* — which is correct, and is
#216's split-or-decline behavior working.

**Open questions: none raised.** So there is nothing to triage under the Gate 1
table. Notable in itself — earlier runs on comparable task files raised several.

## The duplication is the point, not a defect

30 obligations from **19 distinct requirements** — 11 redundant. This is exactly
the condition #144 exists to remove, observed on #144's own task file. Nine
clusters:

| # | Requirement | Obligations |
|---|---|---|
| A | the pass runs after derivation | `task-01`, `task-03`, `constraint-01` |
| B | surviving obligation named by every stating requirement | `task-01`, `constraint-02`, `completion-02` |
| C | union of requirement links and source spans | `task-03`, `constraint-03` |
| D | links are typed fields, not free text | `constraint-04`, `completion-06` |
| E | a reason clause is not a second requirement | `constraint-06`, `completion-04` |
| F | pre-link obligations persisted | `constraint-07`, `completion-05` |
| G | derived obligations change only with own inputs | `constraint-08`, `completion-08` |
| H | links stable unless derived obligations change | `constraint-09`, `completion-09` |
| I | byte-identical runs | `constraint-10`, `completion-07` |

Cluster C is near-verbatim: *"Carry forward the union of requirement links and
source spans from everything merged into a linked obligation"* against *"Carry
forward the union of requirement links and the union of source spans for
everything merged into a linked obligation."*

**Cluster A is a shape not yet recorded on the issue.** It spans Task prose and
Constraints, where #144's Context section describes Constraints/Completion
pairing and #189 added the single-sentence rationale case. Queued as a comment.

## Real finding — attributed to a tool defect

**Scope exclusions reframed inconsistently within one section.** `exclusion-01`
through `-03` became *"handled by another change and is not part of this task's
delivered behavior"*. `exclusion-04` and `-05` became *"**Preserve** the scope
exclusion that …"*, typed `invariant` — a positive obligation downstream stages
will seek test evidence for. The five bullets are worded alike; the split tracks
nothing in the input.

Queued as a filing against **#181**. Not addressed here: prompt wording is
excluded by this task file and owned by #205/#206/#219.

## Task-file authoring note

The issue's Acceptance includes *"Prompt-quality validated by a live run on a
real task file."* That is a statement about how **we** verify, not about what the
software must do, so it is deliberately absent from `current-task.md` and stays
on the issue.
