# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## In flight: #248 — one requirement yields the identical obligation twice

Child of #181. Picked up because `CLAUDE.md`'s sequencing rule puts decomposition
quality ahead of evidence judgement, and #248 is upstream of #242: its duplicate
pair is one of the inputs to the cluster #242 cannot merge.

**Gate 1 run** at `4619e78`, on main, clean tree. Run committed at
`dogfood-logs/248-gate1-run1/`. Agent confirms the breakdown is accurate;
**human confirmation pending** — presented but not yet signed off. If the next
session finds this line unchanged, the gate was never closed.

- 24 requirements, matching the task file exactly; 23 yielded, `completion-01`
  ("Implementation") deliberately none. No invented obligations, none missing.
- **No open questions raised**, so the Gate 1 triage table had nothing to apply.
- One negative finding — an unreconciled linking cluster of four obligations —
  attributed to **#242**, already filed. A comment on it is queued in
  `docs/DEFERRED.md`.

## The plan

Drop an obligation whose description already appears **under the same
requirement**, in `src/acceptance/requirement/obligations.py`, in `decompose`'s
`for item in entry.derived():` loop — before `_unique` mints the id, so no
suffix is minted for a duplicate that is dropped. Record each drop as an
`UnusableAnswer(stage=_STAGE, field="description", ...)`.

Two things settled and worth not re-deriving:

- **Exact string equality**, not normalised. It covers the observed case and
  cannot collapse two obligations that differ in meaning. The issue recommends
  it; recorded as a decision in the queue.
- **Scoped to one requirement's own derivation**, deliberately not to duplicates
  created when #244 re-files an obligation onto another requirement.
  `_resolve_attributions`'s docstring already declares that case the linking
  stage's, and reversing it here would undo #244.

`_Yielded` carries at least one obligation structurally and dedup keeps the
first, so "never left holding none" holds by construction rather than by check.

## Do not rediscover

- **A prompt change invalidates only THAT STAGE's transcripts**, not the whole
  cache — `request_key` hashes each request individually.
- **`git branch -d` refuses every squash-merged branch.** The branch commits
  never enter main's history. Confirm via `gh pr view <n> --json state` then `-D`.
- **`git stash` mid-task reverts the working tree wholesale.** Use a second
  worktree or `git show` to inspect a baseline instead.
- **A `check` over a new task file needs `--mode record`** and makes live calls;
  replay has nothing to replay.
- **`.acceptance/ignore` is committed** (#105) and holds `dogfood-logs/`.
- **`decompose|check --mode record` writes nothing to stdout when redirected** —
  pipe through `tee`.
- **A `PostToolUse` formatter hook reformats files after every edit**, so some
  churn in a diff is not the author's, and an `Edit` right after one may need a
  re-read.
- **Obligation ids are minted per response, not stable across runs** (#231).
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Where the rest of the queue stands

**#180's split** — #251 (re-judge only on changed inputs), #252
(`strongly_supported` is `caught == total`), #253 (determinism as one component),
#254 (report an unreproducible rating) — stays parked behind #181. Each judges an
obligation set that is not trustworthy yet. #251's design is settled and was the
human's; see the issue.

**The open empirical question** before designing #251: how much of #180's
measured churn was decomposition redundancy rather than judgement variance.
`tests/fixtures/rating-stability/` plus the committed dogfood pairs are the
corpus. #248 shrinks one source of that redundancy.
