# Judgement — #269 Gate 1, run 2 (run of record)

`decompose --task current-task.md`, worktree `193-decompose-stability`, branch
`269-decompose-carry-forward` at `992131f`. Run after the run-1 rewrite: the
`## Task` narrative trimmed to mandate, and the redundant `constraint-15`
dropped.

**55 requirements → 54 with obligations, 1 deliberately none, 0 open questions.**

**Verdict: accurate. Gate 1 passes on this run.** Every requirement maps 1:1,
nothing is invented, nothing is lost, and run 1's two inverted obligations are
gone. Three tool findings are recorded below; none of them is a missing or
invented obligation.

## The rewrite worked

Run 1's `rerun-rederive-from-scratch` and `criterion-wording-churn-across-runs` —
obligations requiring the tool to keep the defect #269 removes — do not appear.
`task-01` and `task-02` now yield two obligations that restate the mandate
correctly. The three measurement-derived obligations are also gone.

## Finding 1 — a scope exclusion is typed `human_review`, and the typing moved

`exclusion-01` (*"Inferring that a task file continues a previous run without
being told which run it continues"*) came back typed **`human_review`**. It is a
scope exclusion, and a statically checkable one: it asserts the absence of an
inference path. Typing it `human_review` re-admits an excluded question as an
obligation no test can close.

The movement between runs is the sharper evidence:

| requirement | run 1 type | run 2 type |
|---|---|---|
| `exclusion-01` | `functional` | **`human_review`** |
| `exclusion-06` | **`human_review`** | `functional` |
| `exclusion-07` | **`human_review`** | `functional` |

**The text of all three was byte-identical across the two runs.** The caveat that
keeps this honest: the surrounding registry did change, and the decomposer reads
the whole registry as context on every call (#178), so this is not a controlled
stability measurement. It is still three unchanged requirements whose type
flipped, in both directions, in one edit.

This is the scope-exclusion typing instability queued against **#205**. The
`human_review` type is also the shape that aborted #258's Gate 2, filed as
**#266** — so it is a predicted Gate 2 hazard for this issue.

## Finding 2 — a compound obligation restates four constraints, unlinked

`task-01` yielded `incremental-decomposition-over-recorded-state`, a single
obligation asserting all four cases at once: *"unchanged requirements keep their
previously derived obligations without a model call; edited requirements are
re-derived from prior text, new text, and prior obligations; new requirements are
derived fresh; disappeared requirements have their obligations dropped."*

That restates `constraint-01`, `constraint-04`, `constraint-06` and
`constraint-08`, and **no link was recorded** — it stands as an independent
fifth obligation over the same ground.

Run 1 did link the equivalent restatement: `unchanged-requirement-skips-model-call`
was marked *(also serves constraint-01)* across `task-03` and `constraint-01`.
So the linking stage recognised the restatement in one run and not the next.
Distinct from **#268**, which is about an *inferred* obligation restating an
explicit one — here both are explicit.

**Not rewritten.** A mandate is entitled to state itself once in prose and then
in detail, and cutting the summary to suit the tool would be contorting the input
rather than fixing weak wording. By the tie-break, I do not regret this wording.

## Finding 3 — a scope exclusion is rendered as a prohibition on existing behaviour

`exclusion-03` says prior-review selection for stages other than decomposition —
which `rerun.py::find_prior_review` performs over git ancestry — is out of scope,
meaning this change leaves it alone. The derived obligation reads:

> The change does not perform prior-review selection for stages other than
> decomposition via `rerun.py::find_prior_review` over git ancestry.

Taken as an obligation on the delivered system, that forbids behaviour that
exists today and must keep working. The exclusion has become a prohibition. This
is the **#262** shape — a one-sided requirement derived as something that inverts
what it permits — reached here through a scope exclusion rather than a
constraint.

## What the run got right

- All 35 constraints, 7 scope exclusions and 11 completion expectations mapped
  **1:1**. Nothing invented, nothing lost.
- Every symbol named in the task file survived into its obligation:
  `benchmark/alignment.py::align_obligations`, `rerun.py::find_prior_review`,
  `review_state.py::RequirementDisposition`, `.acceptance/cache/`,
  `tests/fixtures/decompose-stability/`, and
  `tests/test_cli.py::test_two_runs_over_the_same_input_are_byte_identical`.
  Checked by reading, since #193 §3 establishes that symbol loss is invisible to
  both recall and precision.
- `completion-01` (*"Implementation"*) correctly recorded as deliberately
  carrying no obligation, with a reason.
- `exclusion-02` was reframed positively — *"The continued run is named only by
  its identifier"* — which is the right handling of an exclusion and the direct
  contrast with Finding 3.

## Open questions

**None raised.** No triage table, because there is nothing to triage.

Zero is **observed, not confirmed**: #193 establishes that open-question
membership oscillates across runs, and a single draw does not establish an empty
set. Same caveat #191 and #258 recorded at their Gate 1s.
