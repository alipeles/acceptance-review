# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-09*

---

## No task in flight

**#144 landed** as `7c8928d` (PR #233, squash merge). `main` is synced.
`current-task.md` still holds #144's mandate — it is stale, and the next task
overwrites it at Gate 1.

## Next task — #232, and why it is next

**#232 (→ #181): derivation drops the test framing from a Completion
expectation.** One phrased *"A test asserts that X"* is derived into an
obligation stating **X**, so an acceptance criterion becomes indistinguishable
from the behaviour it tests.

It is next because it is lossy and everything downstream inherits it:

- It is why #144's linking merges `constraint-06` with `completion-04` when it
  should not. The linking prompt already carries the negative example for that
  case and it **cannot fire**, because it keys on text that no longer exists by
  the time linking runs. No linking-prompt wording reaches this.
- The framing is unstable across task files. The invoice fixture in
  `tests/prompts/test_linking_prompt.py` keeps *"Add a test that asserts…"* and
  linking correctly declines to merge; this repo's task file drops it.
- Beyond linking: mapping, discrimination and coverage cannot tell the two apart
  either, so a review can report a behaviour addressed while the demanded test
  was never written.

CLAUDE.md's sequencing rule — decomposition quality before evidence quality —
puts it ahead of the #183 / #185 work.

## What #144 shipped

- `requirement/linking.py` — post-derivation pass. **One question per obligation
  pair**, swept completely, batched through `partition.py` at
  `DEFAULT_LINK_PAIR_BATCH_SIZE = 25`.
- Pairs ordered **by distance** between obligations, not by first obligation.
  The natural nesting put all N-1 pairs of obligation 0 into the opening batches
  and reproduced the selection framing one level down.
- `_PairVerdict` declares **`reason` before `same_requirement`** — structured
  output generates in field order, so a verdict first meant committing then
  rationalising.
- A cluster merges only if it is a **complete clique**; a contradicted component
  merges nothing and is recorded through `UnusableAnswerLog`.
- `Review.derived_obligation_map` persists stage 1's output; `rerun.py` gained
  `derivation_changed`.
- **`decompose` runs the pass too**, and carries the log — otherwise its
  breakdown is not the set `check` reviews.
- `docs/DR-144-pairwise-linking.md`.

Final measurement on this repo's task file: **24 derived → 19 linked, 5 merges,
0 contradictions.**

## Gate 2 never came back clean, and #144 merged anyway

On an explicit human call, recorded in the PR body and in
`dogfood-logs/144-gate2-run5/judgement.md`. The one blocker the task **owned**
(`typed-schemas-pydantic-models`) was closed. What remained:

- four unsupported obligations, all from the mandate's problem statement — **#212**;
- one rated *partially addressed* because the rule is implemented as prompt text
  rather than code, which is a property of the stage.

## Do not rediscover

- **The whole registry is in every derivation prompt** (`obligations.py`,
  `_user_prompt(registry, answer_for)`) — DR-204, on purpose. Any task-file edit
  re-derives everything, so per-requirement stability is not available by
  construction. That is **#231**.
- **Obligation ids are minted per response and are not stable across runs.** Not
  cosmetic: findings link by id and `rerun.py` decides staleness by id.
- **A single call asked to find duplicates among N obligations is a SELECTION
  task** and answers with the nearest plausible partner. That is what DR-144
  replaced, and it over-merged twice first.
- **`decompose|check --mode record` writes nothing to stdout when redirected.**
  Record once, then re-run in replay to capture.
- **The corpus manifest carries provenance markers per recording**
  (`tests/prompts/test_corpus_mechanism.py`). Markers must be fixture-level: a
  pair batch holds only the pairs it was given, so a marker naming one obligation
  is absent from any batch that does not include it.
- **The pair-verdict probe is the highest-yield diagnostic of the #144 work** —
  dump every pair with its verdict, its reason and its batch index. It found both
  root causes. ~20 lines against `_pairs`, `_user_prompt` and
  `_confirmed_clusters`; method described in DR-144.
- **Python here is 3.10**; the repo is `alipeles/acceptance-review`.

## Queue — `docs/DEFERRED.md`

One entry open and unfiled: **`test_materialization_is_deterministic` is itself
non-deterministic in CI** (drafted against #184). Observed on PR #233: run
31346367369 failed on `07-declaration-mismatch`; the next run passed on a
markdown-only commit.

## Known open

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**, **#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**,
**#230**, **#231**, **#232**.
