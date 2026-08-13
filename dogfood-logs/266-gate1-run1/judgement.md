# Judgement — #266 Gate 1, run 1

`decompose --task current-task.md`, at `265bfac`. **Superseded by run 2**, which
is the run of record. Kept because it carries the evidence for two findings.

29 requirements → 28 obligations, one deliberate decline (`completion-01`,
the bare `Implementation` marker — correct). **No open questions**, so the
gate's triage table is empty for this run.

## Findings

### 1. A negation inserted into an `explicit` obligation — tool defect

| | text |
|---|---|
| requirement `constraint-09` | The report distinguishes a criterion for which no test **was** recommended because none can evidence it from a criterion for which no test **was** recommended. |
| derived obligation | The report distinguishes a criterion for which no test was recommended because none can evidence it from a criterion for which no test **was not** recommended. |

The obligation is flagged `explicit`, meaning it claims to restate the
requirement rather than infer from it, and the restatement carries a negation the
source does not. Same family as #262 (a paraphrase that does not preserve
entailment) but a strictly harsher case: #262 widened a quantifier, this reverses
a polarity. Queued as a comment on #262.

Not attributed to my wording, though the wording was also poor — see the rewrite
below. The two are independent: the source sentence is parseable and its meaning
is not in doubt, so the inserted `not` is a derivation failure regardless.

### 2. An `inferred` obligation duplicating an `explicit` one, unreconciled

`task-01` yielded four obligations. Two correctly link onward (`also serves
constraint-03`, `constraint-07`). Of the other two:

- `review-completes-and-reports-with-no-evidence-criteria` restates the Task
  line — fair.
- `no-test-can-evidence-criterion-statement-supported` (`inferred`) reads *"A
  criterion may be answered with a statement that no test can evidence it."*
  `constraint-01`'s `recommendation-may-state-no-test-can-evidence` reads *"A
  test recommendation may state that no test can evidence its criterion."*

Those are the same demand. The linking stage exists to reconcile exactly this and
did not, so the set carries a redundant obligation that will demand its own
evidence downstream. Queued as a filing (child of #181).

## The rewrite

`constraint-09` was genuinely badly worded — a self-comparison whose two halves
differ only by a trailing clause. Split into two plain constraints (`constraint-09`,
`constraint-10`), and `completion-07` likewise. This is the sanctioned rewrite of
weak wording, and it re-armed the gate: run 2 is the re-run.

**The rewrite is not the report.** Both findings above stand and are queued.
