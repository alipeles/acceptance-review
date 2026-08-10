# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## #153 is merging — Gate 2 was not clean, on an explicit human call

Same call as #235, for the same reason: **#180**. Two Gate 2 runs each named
**three** obligations below strongly supported, with **no overlap**, over a diff
of one code fix and two added tests. None was an unmet requirement. A gate that
names a different three each run cannot be converged on by fixing what it names.

Evidence: `dogfood-logs/153-gate2-run1/` and `-run2/`, judgement in run 2.

## What #153 shipped

- **`AdmissibleEvidence{CODE_AND_TESTS, CODE_ONLY}`** on `Obligation` — the third
  axis. Scope exclusions yield obligations again, in **absence form** ("The
  change does not alter X"), marked from the parse.
- **`scope_examined`** on `ImplementationCoverage` and `Obligation` — the
  completeness claim's link, satisfying typed-and-linked for evidence that is an
  absence. Populated from the hunks actually rendered, never from the answer.
- Recommendations skip them before the batch; the verdict skips their test axis
  only; the report says "not applicable — confirmed by code evidence alone" and
  "examined N changes across M files; none breaches this boundary".
- 952 tests, ruff clean. Every new test defect-injected.

## The lesson that repeated three times

**Do not ask the model to honour a distinction — enforce it in code.** The axis
is set from `RequirementRef.section`; recommendations are filtered before the
batch; and cited hunks are dropped for a respected boundary because the model
returned them anyway on 3 of 7 exclusions despite the prompt forbidding it.
#232 and #219 each landed the same move. Assume the next one will too.

## Parallel lanes — two worktrees, outside Google Drive

| Worktree | Branch | Lane |
|---|---|---|
| `~/acceptance-worktrees/153-scope-exclusion-obligations` | `153-…` | checker (merging) |
| `~/acceptance-worktrees/234-materialization-determinism` | `234-…` | benchmark (not started) |

At most one lane may touch a model prompt. **Each lane needs its own `.venv`** —
an editable install bakes an absolute path, so a shared venv imports main's
`src/acceptance` and silently tests the wrong tree. `.env` symlinked.
`.acceptance/cache/` is per-lane and starts empty; the suite doesn't need it.
**Run each lane from a session whose cwd is that worktree** — driving one from
elsewhere means absolute paths, which match none of the relative allow rules.

## Do not rediscover

- **Permission prompts are caused by command shape, not vocabulary.** One
  command per Bash call; patterns may wildcard mid-string; naming `.env` in any
  command prompts regardless. See CLAUDE.md's habits section.
- **Approvals are not recorded anywhere** — only denials are. `.claude/settings.local.json`
  accumulating an exact-command rule is the only trace that something prompted.
- **`pytest` must run from its own tree** — `addopts`/`pythonpath` are
  cwd-relative; absolute invocation collects `tests/fixtures/archetypes`.
- **Dev tooling is unpinned (#240)** — a fresh install got ruff 0.16.2 vs main's
  0.15.22, and 85 lint errors that were purely version skew.
- **Obligation ids are minted per response, not stable across runs** (#231).
- **`decompose|check --mode record` writes nothing to stdout when redirected.**
- **Python here is 3.10**; repo is `alipeles/acceptance-review`.

## Queue — `docs/DEFERRED.md`

Empty. Filed this session: **#240** (child of #184), comments on **#205**,
**#180**, **#234**.

## Known open

**#210**, **#180**, **#193**, **#191**, **#196**, **#178**, **#214**, **#129**,
**#223**, **#224**, **#173**, **#225**, **#227**, **#228**, **#212**, **#231**,
**#234**, **#236**, **#240**.
