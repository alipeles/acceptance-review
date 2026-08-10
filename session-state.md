# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## No task in flight here

**#234 landed** as `64ed0c4` (PR #238, squash merge), CI green. `current-task.md`
still holds its mandate — stale, and the next task overwrites it at Gate 1.

**#153 is in flight in a parallel session**, on branch
`153-scope-exclusion-obligations`. Do not pick it up, and expect that session to
rewrite this file when it lands.

## What #234 fixed, and the part worth keeping

`materialize_archetype` committed the **base** blob for a file the head tree
changed, so `test_materialization_is_deterministic` failed about one CI run in
ten on `07-declaration-mismatch`.

`git add -A` decides a file is unchanged from cached stat data — size, mode,
mtime — and `shutil.copy2` preserves mtime and mode, leaving **size** as the only
field that can give a replacement away. `07-declaration-mismatch` is the one
archetype whose base and head `users.py` are both 60 bytes. Fix: `git read-tree
--empty` before `git add -A`, so there is no stat to trust and every file is
hashed from content.

**Reproducing a stat-cache bug:** run materialization under
`core.checkStat=minimal` + `core.trustctime=false` (via `GIT_CONFIG_COUNT`/
`GIT_CONFIG_KEY_n` env vars, which the subprocesses inherit). That is git
comparing exactly those three fields, and it turns a one-in-ten flake into a
deterministic failure on any platform. The three tests in
`tests/benchmark/test_fixtures.py` use it.

## Queue — `docs/DEFERRED.md`

One open: **`ruff check .` reports 85 pre-existing errors.** Verified as ruff's
own defaults widening (`ruff check --isolated` still flags them), not repo
config and not new code; ruff is unpinned in `[project.optional-dependencies]`.
CI cannot catch it — step 4 is `ruff check . || echo "…skipping"`, which
swallows the exit code.

**Fold in with it, found on #238's CI run:** `actions/checkout@v4` and
`actions/setup-python@v5` declare Node 20, which runners now force onto Node 24
and will eventually stop shimming. Current majors are **v7.0.1** and **v7.0.0**.
Check `fetch-depth: 0` still behaves across the bump — #190's cases materialize
worktrees at pinned revisions and fail by name under a shallow clone.

Both are `ci.yml` maintenance and sensibly become one issue.

## Do not rediscover

- **`.acceptance/ignore` is committed** (#105) and holds `dogfood-logs/`. Without
  it, `check` reads the working tree as head and a run's own redirected
  `output.log` joins the diff it is reviewing.
- **`decompose|check --mode record` writes nothing to stdout when redirected** —
  pipe through `tee`, which works.
- **A `PostToolUse` formatter hook reformats files after every edit.** It strips
  imports added ahead of their first use, and re-collapses line wrapping if you
  revert it — so some formatting churn in a diff is not the author's.
- **`gh pr create` with "Closes #a, #b, #c" only closes the first.**
- **Obligation ids are minted per response, not stable across runs** (#231).
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Known open

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**, **#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**,
**#231**, **#237**.
