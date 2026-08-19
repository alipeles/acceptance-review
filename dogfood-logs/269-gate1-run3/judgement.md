# Judgement — #269 Gate 1, run 3 (run of record)

`decompose --task current-task.md`, worktree `193-decompose-stability`, branch
`269-decompose-carry-forward` reset to `origin/main` at **`9def9e7`**.

**Why this run exists:** runs 1 and 2 were made against the pre-#271 tool. #271
(closing #266) rewrote `requirement/obligations.py`, replaced
`AdmissibleEvidence` with `RequiredEvidence`, moved the evidence decision into
decomposition, and re-recorded the decomposition transcripts. That invalidates
both earlier runs as a Gate 1 record. **Task file byte-identical to run 2** — the
only variable is the tool.

**55 requirements → 54 with obligations, 1 deliberately none, 0 open questions.**

**Verdict: Gate 1 passes.** Coverage is complete and correct — all 35
constraints, 7 exclusions and 11 completion expectations map, nothing invented,
nothing missing. Three findings below, one of which is new and one of which #271
partly fixed.

## What #271 changed here

`task-01` went from **1 obligation to 6**, and `task-02` from 1 to 4. The
compound obligation that run 2 produced is now broken into its parts, and two of
the ten are correctly linked:

- `constraint-01-unchanged-requirement-no-model-call` — *(also serves constraint-01)*
- `every-run-reports-identifier` — *(also serves constraint-20)*

Run 2's Finding 2 said linking reconciled a prose restatement in run 1 and not in
run 2. It reconciles again here — so that finding is **not a regression that
persists**; what persists is narrower and is Finding 1 below.

## Finding 1 — four restatements of explicit constraints stand unlinked

Of `task-01`'s six obligations, one is linked and four restate an explicit
constraint with no link recorded:

| obligation from `task-01` | restates | type |
|---|---|---|
| `unchanged-requirement-carries-obligations` | `constraint-02` / `-03` | **inferred** |
| `edited-requirement-rederived-from-old-and-new-text` | `constraint-04` | explicit |
| `new-requirement-derived-fresh` | `constraint-08` | explicit |
| `disappeared-requirement-drops-obligations` | `constraint-06` | explicit |

The last is the sharpest: `constraint-06` produced
`drop-obligations-for-removed-requirement` and `task-01` produced
`disappeared-requirement-drops-obligations` — near-identical ids, same assertion,
no link. `task-02` adds two more (`run-records-derived-work`,
`later-run-can-name-continued-run`), both `inferred`.

`unchanged-requirement-carries-obligations` is **exactly #268** — an *inferred*
obligation restating an explicit one without reconciliation. The three explicit
ones are the same defect on the explicit/explicit axis, which #268 does not
cover.

Net effect: the obligation set is inflated by six restatements, each of which
will independently demand evidence at Gate 2.

**Not rewritten.** The `## Task` section is two paragraphs of plain mandate with
no background left in it. Cutting it further to stop the tool duplicating it
would be contorting the input, and by the tie-break I do not regret this wording.

## Finding 2 — a scope exclusion is still a prohibition, and now it has lost its symbol

`exclusion-03` says prior-review selection for stages other than decomposition —
which `rerun.py::find_prior_review` performs over git ancestry — is out of scope.
Run 3 derives:

> The change does not perform prior-review selection for stages other than
> decomposition.

Two defects, one of them new:

1. **Still a prohibition on behaviour that must keep working**, as in run 2. As
   an obligation on the delivered system this forbids what `find_prior_review`
   does today. Contrast `exclusion-02` in the same run, correctly reframed.
2. **The symbol `rerun.py::find_prior_review` is gone.** Run 2 retained it in
   the obligation text; run 3 dropped it. This is #193 §3 — symbol loss is
   invisible to both recall and precision, because the aligner correctly matches
   an obligation that dropped its symbol to one that kept it. Caught by reading,
   which is the only way it can be caught.

## Finding 3 — scope-exclusion typing has now moved three ways

| requirement | run 1 | run 2 | run 3 |
|---|---|---|---|
| `exclusion-01` | `functional` | `human_review` | `regression` |
| `exclusion-06` | `human_review` | `functional` | `human_review` |
| `exclusion-07` | `human_review` | `functional` | `human_review` |

Text byte-identical throughout. `exclusion-06` and `-07` have now returned to
`human_review` after passing through `functional`.

**The honest caveat, and it is a real limit on this evidence:** no two of these
three runs share both a tool version and a surrounding registry. Runs 1→2 changed
the task file's `## Task` section; runs 2→3 changed the tool. The decomposer
reads the whole registry as context on every call (#178), so neither pair is a
controlled comparison. This is corroborating evidence for the instability, **not
a measurement of it**. A controlled test — perturb one unrelated bullet, hold the
tool fixed, watch these three types — is #193/#205's work, not this issue's.

## What the run got right

- All 35 constraints, 7 exclusions, 11 completion expectations mapped, nothing
  invented, nothing lost.
- Linking reconciled two restatements across sections (`constraint-01`,
  `constraint-20`) — the mechanism works, it is under-applied.
- `completion-01` (*"Implementation"*) correctly carries no obligation, with a
  reason.
- Symbols retained everywhere except `exclusion-03`:
  `benchmark/alignment.py::align_obligations`,
  `review_state.py::RequirementDisposition`, `.acceptance/cache/`,
  `tests/fixtures/decompose-stability/`, and
  `tests/test_cli.py::test_two_runs_over_the_same_input_are_byte_identical`.

## Minor, recorded but not filed

`constraint-26`'s obligation description ends *"No ledger file is written under
`.acceptance/cache/."* — an unbalanced backtick, the closing one lost. Cosmetic.

Obligation id minting is inconsistent: some carry a redundant requirement-id
prefix (`constraint-01-…`, `completion-09-…`, `completion-11-…`) and most do not.
Cosmetic, but it is identity churn in the ids — the exact axis #269 exists to
stabilise, so worth watching rather than filing.

## Open questions

**None raised.** Zero is observed, not confirmed — #193 establishes that
membership oscillates, and one draw does not establish an empty set.
