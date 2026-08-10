# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## In flight: #228 — a benchmark case yielding zero requirements must fail, not score

Branch `228-benchmark-empty-registry`, branched from `0923f77` (= `origin/main`).
Child of **#186**. Two commits: `e67c615`, `0514119`.

**One of three parallel lanes** — #180 and #214 are running in their own
sessions. **This lane touches no model prompt.**

## Gate 1: PASSED. Gate 2: NOT CLEAN — blocked on a mapping defect, awaiting a human call

Four runs saved under `dogfood-logs/228-gate1-run{1,2}/` and
`dogfood-logs/228-gate2-run{1,2}/`, each with its judgement.

## Where it stands

**The code is done and verified.** Suite green (**1005 passed**), ruff clean,
and **defect injection confirms the tests bite**: short-circuiting
`require_nonempty_registry` fails 8 of the guard file's 31 tests, including the
new paired control, while the control half keeps passing.

**Gate 2 will not converge.** Run 1 named three obligations; all three were real
and all three are fixed. Run 2 named a **disjoint two** — both of which were
*strongly supported in run 1*, over tests that did not change.

## The blocking finding — #182, cross-referenced #180

Where a Completion expectation ("A test asserts that X") sits beside its
Constraint twin ("X"), mapping attaches the tests to one or the other, unstably.
Run-2's report **contradicts itself**: obligation 3 says no test iterates both
corpora; obligation 8 cites those exact tests as strong evidence; unrequested
change #5 calls them surplus. Full evidence in
`dogfood-logs/228-gate2-run2/judgement.md`.

Not addressable in code — the tests it asks for exist. Writing duplicates to
move a label is the "fix the output, not the wording" failure CLAUDE.md forbids.

**Decision needed:** merge on an explicit human call as #153 and #235 did, or
hold #228 behind a mapping fix.

## What run 1 caught that was real

- **`byte-identical-review-state`** was a Constraint with no corresponding
  change. My authoring defect — a standing invariant, not a requirement of this
  change. Moved to Scope exclusions; confirmed by non-violation in run 2.
- **task-01 `instead of being scored`** had no test aimed at it. Ten tests
  asserted the guard raises; none asserted no number is produced. Added the
  paired control test the recommendation prescribed. Strongly supported in run 2.

## The change

- `benchmark/case.py` — `EmptyRequirementRegistryError` + `require_nonempty_registry`,
  which runs the real `parse_task_file` → `build_registry`, not a heading proxy.
- Called by all three corpus builders **before** materialization:
  `build_benchmark_case`, `build_decompose_case`, `build_corpus_case`.
- `tests/benchmark/test_empty_registry_guard.py` — 31 tests.
- `requirement/obligations.py` — corrected a comment stale since `1c53592`.

## Verified facts worth keeping

- Every task file in `archetypes/` (13), `decompose-regression/` (8) and
  `rating-stability/` (6) parses non-empty. The guard changes no current
  outcome, so the corpus cannot demonstrate it — hence the test-supplied file.
- `test_region_coverage.py` parametrizes over `dogfood-logs/*/current-task.md`,
  so **adding a dogfood log adds tests**. That is why the suite count jumps by
  more than the tests you wrote.
- Synthetic cases in `test_runner.py`, `test_scoring.py`, `test_alignment.py`,
  `test_case.py` use task text with no `# Task` heading and therefore yield
  **empty registries too**. That is why the guard is on the builders, not at
  hook entry. Filed as **#243**.

## Queue — `docs/DEFERRED.md`

**One open filing:** the mapping defect above, drafted in full as a child of
**#182**. Needs approval before filing.

Filed this session: **#243** (`run_case`'s acceptance test cannot fail), child
of #186.

## Do not rediscover

- **`.acceptance/ignore` is committed** (#105) and holds `dogfood-logs/`.
- **`decompose|check --mode record` writes nothing to stdout when redirected** —
  pipe through `tee`. A first `check` on new task text needs `--mode record`.
- **A `PostToolUse` formatter hook reformats files after every edit.** It strips
  imports added ahead of their first use — add the import in the same edit as
  the code that uses it, or it silently vanishes.
- **Permission prompts are caused by command shape, not vocabulary.** One command
  per Bash call; naming `.env` in any command prompts regardless.
- **`pytest` must run from its own tree** — `addopts`/`pythonpath` are
  cwd-relative. Each parallel lane needs its own `.venv`.
- **`gh api … -f` sends strings; sub-issue ids need `-F`** to be integers.
- **`gh pr create` with "Closes #a, #b, #c" only closes the first.**
- **Obligation ids are minted per response** (#231); types move too (#205).
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Known open

**#210**, **#180**, **#193**, **#191**, **#196**, **#178**, **#214**, **#129**,
**#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**, **#231**,
**#236**, **#237**, **#239**, **#243**.
