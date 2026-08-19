# Judgement — #269 Gate 1, run 1

`decompose --task current-task.md`, worktree `193-decompose-stability`, branch
`269-decompose-carry-forward` at `992131f`.

**57 requirements → 56 with obligations, 1 deliberately none, 0 open questions.**

**Verdict: the breakdown is not one I would defend.** The `## Task` narrative
produced five obligations, two of which require the tool to keep the exact defect
#269 exists to remove. Task file rewritten and re-run as run 2.

## Finding 1 — the problem statement is derived as an obligation to preserve the problem

The `## Task` section describes current behaviour in the present tense. Two
obligations came back requiring that behaviour to continue:

| obligation | text | why it inverts |
|---|---|---|
| `rerun-rederive-from-scratch` [functional/explicit] | *"Decomposition is re-derived from scratch on every run, and a changed task invalidates everything because obligations are a function of the task text."* | This is the defect being removed, derived as a requirement to keep it. |
| `criterion-wording-churn-across-runs` [functional/explicit] | *"Across three runs of one unchanged task file differing only by seed, criterion wording churn occurs, with identifiers re-minted alongside the wordings."* | Requires the churn the task exists to eliminate. |

Both are satisfied by **not** doing the task. A correct implementation would be
scored as failing them.

This is not the #262 shape (a one-sided requirement derived as two-sided). It is
narrower and worse: descriptive prose about the *status quo* is read as
prescriptive. A client mandate is entitled to open by saying what is wrong today,
so the tool must not convert that into a requirement to preserve it.

**Disposition: both.** The wording is genuinely weak for this input format and is
rewritten (the sanctioned edit), *and* the inversion is queued as a filing —
rewriting my own file does not make the tool behaviour correct.

## Finding 2 — completed measurements are derived as obligations

Three more from the same narrative, none of them properties of the change:

- `criterion-churn-preserves-content` [regression] — *"Across three runs … no
  obligation content is lost."* A measurement already taken, before this change.
- `not-model-nondeterminism` [explanation_observability] — an established
  finding about the cause.
- `task-text-is-prompt-for-later-stages` [functional] — rationale for why the
  work matters.

Same root cause as Finding 1, same disposition; carried on the same filing.

## Finding 3 — two scope exclusions are typed `human_review`

`exclusion-06` and `exclusion-07` — what the decomposer derives and how it words
an obligation it derives fresh — came back typed `human_review`. Both are scope
*exclusions*: they exist to remove those questions from the review, and typing
them `human_review` re-admits them as obligations no test can ever close.

This is the shape that aborted #258's Gate 2 and is filed as **#266** (a weak
obligation no test can evidence aborts the whole review). It also touches the
queued scope-exclusion typing instability noted against **#205**. Flagged here as
a predicted Gate 2 hazard for this issue, not as a new defect.

## Finding 4 — redundancy in the task file, mine

`constraint-14` (*"No obligation is carried forward when no continued run is
named"*) and `constraint-15` (*"The carried state … is empty"*) assert the same
property twice, and produced two obligations. My wording; `constraint-15` is
dropped in run 2. Not a tool finding.

## What the run got right

Worth recording, because it is the part that has to keep working:

- The 36 constraints, 7 exclusions and 11 completion expectations mapped **1:1**,
  with nothing invented and nothing lost.
- `unchanged-requirement-skips-model-call` is **shared** between `task-03` and
  `constraint-01` rather than duplicated — linking recognised the restatement.
- Every symbol named in the task file survived into the obligation derived from
  it: `rerun.py::find_prior_review`, `benchmark/alignment.py::align_obligations`,
  `review_state.py::RequirementDisposition`, and
  `tests/test_cli.py::test_two_runs_over_the_same_input_are_byte_identical`. This
  is the axis #193 §3 says is invisible to recall and precision, so it is checked
  by reading, not by a metric.
- `completion-01` (*"Implementation"*, a bare section marker) was correctly
  recorded as deliberately carrying no obligation.

## Caveat on the zero

Zero open questions is **observed, not confirmed** — the same caveat #258 and
#191 recorded. #193 establishes that membership oscillates across runs, and a
single draw does not establish that the set is empty.
