# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## In flight — #234, branch `234-materialization-determinism`

`test_materialization_is_deterministic` fails intermittently in CI: two
materializations of `07-declaration-mismatch` in one process produced different
`head_sha`. Child of #184. A parallel session holds #153 — do not touch it.

Branched from `4b78d62`; no implementation committed yet.

## Gate 1 — clean at `4b78d62`, confirmed by Claude, presented for human sign-off

`dogfood-logs/234-gate1-run1` and `-run2`. Run 2 is the clean one: 13
requirements, 10 obligations, 3 exclusions disposed of uniformly, **no open
questions**.

Run 1 raised one finding: a bare `Implementation` bullet under Completion
expectations was disposed of with the reason *"out of scope for this change"* —
inverting the section it came from. Queued as a filing against **#181**; the
weak bullet was removed under the sanctioned rewrite and the gate re-armed.

## The cause is identified — this is the load-bearing part

**`git add -A` trusted a stale index stat-cache and re-used the base blob.**
Proven, not inferred:

- The head commit recorded `base/users.py`'s content while adding
  `head/test_users.py`. Rebuilding exactly that tree by hand reproduces
  `1f50fdb860fdaca912ad300bd7ae0774e0eab7eb` — the CI failure's `first.head_sha`,
  to the digit. The correct tree is `143940c7e9c9…5d73d697f4ade`, CI's `second`.
- **07 is the only archetype whose `base/` and `head/` counterparts are the same
  size** — `users.py`, 60 bytes both, different content. Every other fixture's
  head file differs in size, so git always re-hashes it. That is why exactly one
  archetype ever failed.
- `shutil.copy2` preserves mtime and mode. Same size + same mtime + same mode is
  all `git add` compares before deciding a file is unchanged.
- Deterministic repro on any platform: run materialization with
  `core.checkStat=minimal` and `core.trustctime=false`, which is the comparison
  the runner effectively made. Current code then emits the bad SHA every time.

**Fix:** empty the index before staging, so `add -A` has no cached stat to trust
and hashes from content — `git read-tree --empty` then `git add -A`, in
`materialize_archetype`. Verified at the git level under the hostile config:
bad SHA before, correct SHA after.

## Next

Implement the fix in `src/acceptance/benchmark/fixtures.py`, add the three
demanded tests to `tests/benchmark/test_fixtures.py`, then Gate 2 (`check`).

## Do not rediscover

- **Back-to-back materialization does not reproduce this** — 20 iterations over
  all 13 fixtures, 0 mismatches. It needs the stat-comparison condition forced.
- **`.acceptance/ignore` is committed** (#105) and holds `dogfood-logs/`. Without
  it, `check` reads the working tree as head and a run's own redirected
  `output.log` joins the diff it is reviewing.
- **`decompose --mode record` writes nothing to stdout when redirected** — pipe
  through `tee`, which works.
- **`gh pr create` with "Closes #a, #b, #c" only closes the first.**
- **Obligation ids are minted per response, not stable across runs** (#231).
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Queue — `docs/DEFERRED.md`

One open: the inverted disposal reason above, drafted against #181.

## Known open

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**, **#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**,
**#231**, **#234**.
