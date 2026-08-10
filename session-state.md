# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-08*

---

## Task in flight — #144, merge semantically duplicate obligations

Branch `144-merge-duplicate-obligations`, cut from `main` at `9724df4`.
`main` is pushed; nothing on this branch is pushed.

**PR #233 open.** Branch pushed. **Gate 2 was NOT clean and the PR was opened
anyway, on an explicit human call** — recorded in the PR body, not only here.
Five check runs in `dogfood-logs/144-gate2-run{1..5}/`; run 5 is the current one:
24 derived → 19 linked, 5 merges, 0 contradictions, 15 strongly supported,
4 unsupported. The one blocker this task owned (`typed-schemas-pydantic-models`)
is closed; the four unsupported are #212's and the one partially-addressed
obligation is a prompt-implemented rule.

Gate 1 passed at `e34aebc`, human-confirmed on run 3.
Three runs in `dogfood-logs/144-gate1-run{1,2,3}/`. Run 3 is the current one:
27 requirements, 21 with obligations, 6 deliberately none, 24 obligations,
**no open questions**. All 11 Constraints and all 7 Completion expectations
carry exactly one obligation; the six declines are the five Scope exclusions
and `Implementation`.

## Two decisions taken at this gate

1. **Do not partition the linking pass.** It reasons across all obligations at
   once, so batching decides which pairs *can* be compared — a duplicate split
   across batches is silently under-merged, and under-merging is the failure this
   issue deliberately tolerates, so the damage would be invisible. Record the
   observed obligation count in provenance instead, and measure the ceiling.
2. **Stage-1 determinism is a task-file-level guarantee, not per-requirement.**
   Unchanged task text ⇒ byte-identical review state at both stages
   (`constraint-10`). Per-requirement locality was removed from the task file
   after being measured false, and is now **#231**.

## What #144 must build

| File | Change |
|---|---|
| `requirement/linking.py` | **new** — post-derivation pass, schema-constrained, typed links |
| `review_state.py` | new persisted field: the pre-link per-requirement obligation set |
| `serialization.py` | canonical form for it — byte-identical reruns depend on it |
| `pipeline.py` | call it after `decompose`, before mapping |
| `rerun.py` | second staleness question: derivation output vs. the merge |

Interface others depend on: an `Obligation` gains a **list** of requirement
links, not a single owner; the response schema has no free-text path to a link.

## Filed this session

- **#230** (→ #181) — scope exclusions reframed inconsistently within one section.
  **Widen it**: run 3 declined all five uniformly with the bullets unchanged, so
  the defect is instability, not inconsistency. Widening comment filed.
- **#231** (→ #184) — derived obligations are not local to their requirement; a
  two-line edit re-split two untouched requirements and churned 27 of 33 ids.
- **#232** (→ #181) — derivation drops "A test asserts that" from a Completion
  expectation, so an acceptance criterion becomes indistinguishable from the
  behaviour it tests. **This is the load-bearing remaining defect**: it is why
  `constraint-06` and `completion-04` merge when they should not, and no
  linking-prompt wording reaches it.
- Comment on **#144** — 30 obligations from 19 distinct requirements, nine
  clusters, and a third source-span shape (Task prose ↔ Constraints, three-way).

## Do not rediscover

- **The whole registry is in every derivation prompt** (`obligations.py:289`,
  `_user_prompt(registry, answer_for)`). That is DR-204 on purpose. It means any
  task-file edit changes every batch's request key and re-derives everything, so
  per-requirement stability is not available by construction. This is #231.
- **Obligation ids are minted per response and are not stable across runs.**
  Between runs 1 and 2, 27 of 33 ids changed while 27 of 29 requirements kept the
  same obligation *count* — most of the churn was a naming-convention shift. Ids
  are not cosmetic: findings link by id and `rerun.py` decides staleness by id.
- **The model minted the same obligation id twice in run 3**
  (`reason-clause-counts-as-same-requirement` and `…-2`) for `constraint-06` and
  `completion-04`. Its own naming says they are one requirement.
- **`decompose --mode record` writes nothing to stdout when redirected.** Record
  once, then re-run in replay to capture.
- **Python here is 3.10**; the repo is `alipeles/acceptance-review`.

## Repo housekeeping landed this session

`4acc5fe` — the working agreement now points at the real dogfood gates instead of
an invented milestone pair; non-blocking defects, filings and decisions bundle
into `docs/DEFERRED.md` and are reviewed at the next gate. `.claude/commands/gate.md`
deleted. `9724df4` — allowlist the `.venv/bin/` commands the repo actually runs;
`settings.local.json` pruned 115 → 5 entries.

## Known open, not this task's problem

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**, **#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**,
**#230**, **#231**.
