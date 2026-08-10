# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## No task in flight

**#214 landed** as `7573697` (PR #247). **#228 is merging** as PR #246 — Gate 2
not clean, on an explicit human call. **#180 is still in flight** in its own
session.

`current-task.md` holds #228's mandate; stale, and the next task overwrites it
at Gate 1.

## Why #228 merged without a clean gate

Third time, same cause. **#153** and **#235** made the same call before it. The
new part is that #228's evidence isolates the failure to the **mapping call**,
filed as **#245** against #182, and does it without needing to compare runs.

Run 2's report contradicts itself three ways:

- obligation 3 (`completion-04`): `unsupported`, *"no mapped test"*, recommending
  a test that iterates both corpora;
- obligation 8 (`constraint-04`): **strongly supported**, citing
  `test_every_archetype_task_file_yields_requirements` and its
  decompose-regression twin — the very tests obligation 3 says do not exist;
- unrequested change #5: calls those same tests surplus to requirements.

Across runs, the mapper moved the tests between a Completion expectation ("A test
asserts that X") and its Constraint twin ("X"), and in run 2 handed one to a
**scope exclusion** — a code-evidence-only obligation that should attract no test
mapping at all.

Run 1 named three obligations; **all three were real and all three were fixed**.
Run 2 then named a disjoint two that run 1 had passed, over unchanged tests.

Evidence: `dogfood-logs/228-gate2-run1/` and `-run2/`, judgement in run 2.

## What #228 shipped

- **`benchmark/case.py::require_nonempty_registry`** + `EmptyRequirementRegistryError`.
  Runs the real `parse_task_file` → `build_registry`, **not** a `# Task` heading
  proxy: a proxy would pass exactly when the parser changed its mind about what
  a requirement is, which is the case worth catching.
- Called by all three corpus builders **before materialization** —
  `build_benchmark_case`, `build_decompose_case`, `build_corpus_case`.
- 31 tests. **Injection-verified:** short-circuiting the guard fails 8 of them.

## The lesson worth keeping from #228

**A test that cannot fail is not evidence, and neither is a passing corpus.**
Every task file in all three corpora parses non-empty today, so the corpus can
never demonstrate the guard — the firing tests must supply their own unreadable
file. The same reasoning found the defect in the *runner's* own acceptance test
(**#243**): it asserts `gap_recall == 0.0` over an input with nothing to find,
so it would pass against a checker that found every gap.

Corollary that keeps recurring: **assert the consequence, not just the
mechanism.** Ten tests asserted the guard raises; none asserted that no number
is produced. Gate 2 caught that, and the recommendation correctly demanded a
*control* — "no score" is worthless without showing the harness would have
produced one.

## Parallel lanes — what worked

Three lanes, two landed the same day, no code conflict. Conditions that held:

- **No lane touched a model prompt except its own** — the request key hashes it.
- **Each lane had its own `.venv`** (editable installs bake an absolute path).
- **Each ran from a session whose cwd was its worktree** — absolute paths match
  none of the relative allow rules and prompt on every call.
- **Conflicts were only ever `current-task.md` and `session-state.md`**, which
  every lane rewrites wholesale. Resolve with `git checkout --ours` and move on.
- Cross-lane messaging was worth it: #214's session confirmed no API overlap
  before I looked, which saved a full audit of `verdict.py`/`pipeline.py`.

## Do not rediscover

- **`.acceptance/ignore` is committed** (#105) and holds `dogfood-logs/`.
- **`decompose|check --mode record` writes nothing to stdout when redirected** —
  pipe through `tee`. A first `check` over new task text needs `--mode record`.
- **The `PostToolUse` formatter strips imports added ahead of their first use.**
  Add the import in the same edit as the code using it, or it silently vanishes.
- **`test_region_coverage.py` parametrizes over `dogfood-logs/*/current-task.md`**,
  so adding a dogfood log adds tests — the suite count grows by more than you wrote.
- **Synthetic cases in `test_runner.py`, `test_scoring.py`, `test_alignment.py`
  and `test_case.py` yield empty registries too** (`## Deliverable` is not a
  recognised heading). That is why #228's guard is on the builders and not at
  hook entry. Filed as **#243**.
- **`gh api … -f` sends strings; sub-issue ids need `-F`** to be integers.
- **`gh pr create` with "Closes #a, #b, #c" only closes the first.**
- **Obligation ids are minted per response** (#231); types move too (#205).
- **`pytest` must run from its own tree** — `addopts`/`pythonpath` are cwd-relative.
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Queue — `docs/DEFERRED.md`

Empty. Filed this session: **#243** (child of #186), **#245** (child of #182).

## Known open

**#210**, **#180**, **#193**, **#191**, **#196**, **#178**, **#129**, **#223**,
**#224**, **#173**, **#225**, **#227**, **#212**, **#231**, **#236**, **#237**,
**#239**, **#243**, **#245**.
