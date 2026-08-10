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

**#234 landed** as `64ed0c4` (PR #238), CI green. **#153 is merging** as PR #241
— Gate 2 not clean, on an explicit human call. `current-task.md` holds #153's
mandate; stale, and the next task overwrites it at Gate 1.

Both lanes ran in parallel worktrees and both are now done.

## Why #153 merged without a clean gate

Same call as #235, same cause: **#180**. Two Gate 2 runs each named **three**
obligations below strongly supported, with **no overlap**, over a diff of one
code fix and two added tests. None was an unmet requirement. A gate that names a
different three each run cannot be converged on by fixing what it names.

Evidence: `dogfood-logs/153-gate2-run1/` and `-run2/`, judgement in run 2, filed
on #180.

## What #153 shipped

- **`AdmissibleEvidence{CODE_AND_TESTS, CODE_ONLY}`** on `Obligation` — a third
  axis, separate from `type` / `coverage_status` / `evidence_class`. Scope
  exclusions yield obligations again, in **absence form** ("The change does not
  alter X"), marked from the parse.
- **`scope_examined`** — the completeness claim's link, satisfying
  typed-and-linked for evidence that is an absence. Refines #133's "empty
  `diff_refs`" into a recorded claim.
- Recommendations skip them before the batch; the verdict skips their test axis
  only (a breach is still a material gap); the report says "not applicable —
  confirmed by code evidence alone" and "examined N changes across M files; none
  breaches this boundary".

## What #234 fixed

`materialize_archetype` committed the **base** blob for a file the head tree
changed. `git add -A` trusts cached stat data — size, mode, mtime — and
`shutil.copy2` preserves mtime and mode, leaving **size** as the only giveaway;
`07-declaration-mismatch` is the one archetype whose base and head `users.py` are
both 60 bytes. Fix: `git read-tree --empty` before `git add -A`.

**Reproducing a stat-cache bug:** run under `core.checkStat=minimal` +
`core.trustctime=false` via `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`, which
subprocesses inherit. Turns a one-in-ten flake into a deterministic failure.

## The lesson that repeated three times in #153

**Do not ask the model to honour a distinction — enforce it in code.** The axis
is set from `RequirementRef.section`; recommendations are filtered before the
batch; and cited hunks are dropped for a respected boundary, because the model
returned them anyway on 3 of 7 exclusions despite the prompt forbidding it.
#232 and #219 each landed the same move. Assume the next one will too.

## Parallel lanes — what to repeat and what not to

Worktrees live in `~/acceptance-worktrees/`, outside Google Drive. It worked, on
these conditions:

- **At most one lane may touch a model prompt** — the request key hashes it, so
  two lanes editing prompts merge into a state neither recorded against.
- **Each lane needs its own `.venv`.** An editable install bakes an absolute
  path, so a shared venv imports main's `src/acceptance` and silently tests the
  wrong tree.
- **Run each lane from a session whose cwd is that worktree.** Driving one from
  elsewhere means absolute paths, which match none of the relative allow rules
  and prompt on every call.
- **Rebase early.** #153 was branched from `4b78d62` and merged five commits
  later; the conflicts were all in `session-state.md` / `current-task.md`, which
  both lanes rewrite wholesale.

## Do not rediscover

- **`.acceptance/ignore` is committed** (#105) and holds `dogfood-logs/`.
- **`decompose|check --mode record` writes nothing to stdout when redirected** —
  pipe through `tee`, which works.
- **A `PostToolUse` formatter hook reformats files after every edit.** It strips
  imports added ahead of their first use — so some churn in a diff is not the
  author's.
- **Permission prompts are caused by command shape, not vocabulary.** One command
  per Bash call; patterns may wildcard mid-string; naming `.env` in any command
  prompts regardless. **Approvals are not recorded anywhere** — only denials are;
  a new exact-command rule in `.claude/settings.local.json` is the only trace.
- **`pytest` must run from its own tree** — `addopts`/`pythonpath` are
  cwd-relative.
- **`gh pr create` with "Closes #a, #b, #c" only closes the first.**
- **Obligation ids are minted per response, not stable across runs** (#231).
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Queue — `docs/DEFERRED.md`

Empty. Filed this session: **#237**, **#239**, comments on **#180**, **#205**,
**#234**, **#239**. **#240** was filed and closed as a duplicate of #239.

## Known open

**#210**, **#180**, **#193**, **#191**, **#196**, **#178**, **#214**, **#129**,
**#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**, **#231**,
**#236**, **#237**, **#239**.
