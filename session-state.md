# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## Task in flight — #153, in a worktree

**Scope exclusions carry no meaning downstream.** Working the revised acceptance
in [#153's 2026-08-10 comment](https://github.com/alipeles/acceptance-review/issues/153#issuecomment-5241310422),
not the original issue body: exclusions **yield obligations again**, marked as
admitting **code evidence only**, with no test-support score.

Branch `153-scope-exclusion-obligations`, worktree at
`/Users/alipeles1/acceptance-worktrees/153-scope-exclusion-obligations`.

## Parallel lanes — two worktrees, outside Google Drive

| Worktree | Branch | Lane |
|---|---|---|
| `~/acceptance-worktrees/153-scope-exclusion-obligations` | `153-…` | checker (this one) |
| `~/acceptance-worktrees/234-materialization-determinism` | `234-…` | benchmark |

Chosen because at most one lane may touch a model prompt: #153 changes the
decomposition prompt, #234 is `benchmark/fixtures.py` git materialization with
no model call at all. **Each lane needs its own `.venv`** — an editable install
bakes an absolute path, so a shared venv would import main's `src/acceptance`
and silently test the wrong tree. `.env` is symlinked. `.acceptance/cache/` is
per-lane and starts empty; the suite doesn't need it (933 pass), only
`decompose`/`check` re-record.

## Gate 1 — PASSED at 4b78d62

Decomposition confirmed accurate by Claude, presented to the human 2026-08-10.
26 requirements → 18 obligations, 8 deliberately none; every constraint
accounted for, none invented, **zero open questions**. Full triage in
`dogfood-logs/153-gate1-run1/judgement.md`.

Two things carried forward:

- **All 7 scope exclusions declined** — correct today, and the defect being
  removed. After the change this task file should yield **25** obligations, not
  18, with 7 on the code-evidence-only axis. That is the Gate 2 tell.
- **`constraint-03` typed `test_demand` and inverted** — the requirement forbids
  a test recommendation. Queued as a filing on **#205**; type assignment is a
  scope exclusion of this task.

## The delicate part of the implementation

`obligations.py`'s prompt currently says *"Dispose of every requirement in
[Scope exclusions] as `no_obligation`"*, and its rationale is sound: the only
way it knew to produce an obligation was by **inversion**, which is what
#219/#230 fixed (4/6 inverted → 0/6). #153 needs a **third** form — an
obligation whose demand is the *absence* of the excluded work — without
reopening inversion. New tests must pin non-inversion, not just presence.

## Do not rediscover

- **Prompts are matched by shape, not vocabulary** — see CLAUDE.md's habits
  section, rewritten at 41a4af9/813fa71/4b78d62. One command per Bash call;
  `(cd <dir> && …)` subshells; patterns may wildcard mid-string
  (`Bash(git -C * add *)`); a specific `allow` beats a broad `ask`
  (`git merge --ff-only` verified).
- **Naming `.env` in any command prompts**, overriding `Bash(ls *)`.
- **`pytest` must run from its own tree** — `addopts`/`pythonpath` are
  cwd-relative; absolute-path invocation collects `tests/fixtures/archetypes`
  as suite tests and errors.
- **Obligation ids are minted per response, not stable across runs** (#231).
- **`decompose|check --mode record` writes nothing to stdout when redirected.**
- **Python here is 3.10**; repo is `alipeles/acceptance-review`.

## Queue — `docs/DEFERRED.md`

One open: the `constraint-03` mis-type, drafted as a comment on #205.

## Known open

**#210**, **#180**, **#193**, **#153**, **#191**, **#196**, **#178**, **#214**,
**#129**, **#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**,
**#231**, **#234**, **#236**.
