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

Three parallel lanes ran and all three landed, CI green on each:

| | | |
|---|---|---|
| **#214** | `7573697` (PR #247) | mandate coverage bounds the completion verdict |
| **#228** | `75fefc4` (PR #246) | a benchmark case yielding no requirements fails instead of scoring |
| **#244** | `5047088` (PR #255) | an obligation is filed under the requirement its quotation comes from |

Worktrees and branches for all three are removed. `docs/DEFERRED.md` is empty.

## Where #180 stands, since that is what the next session will pick up

**#180 was split** into **#251** (re-judge only on changed inputs), **#252**
(`strongly_supported` is `caught == total`), **#253** (determinism as one
component) and **#254** (report an unreproducible rating). #180 stays open as the
measurement and corpus they close into; see its comment thread for the split.

**Do not start those yet.** #244 fixed one decomposition defect and found two
more — **#248** (one requirement yields the identical obligation twice) and a
remaining unreconciled-linking cluster. Every one of #251–#254 judges an
obligation set that is not yet trustworthy, so `CLAUDE.md`'s sequencing rule
(decomposition quality before evidence judgement) still points at **#181**.

**The open empirical question**, worth answering before designing #251: how much
of #180's measured churn was decomposition redundancy rather than judgement
variance. Redundant obligations are rated independently, so three obligations
stating one requirement can carry three different ratings — instability with a
perfectly consistent judge. `tests/fixtures/rating-stability/` plus the committed
dogfood pairs are the corpus to answer it against.

**The design in #251 is settled and was the human's**, not the agent's: do not
re-judge a criterion whose own inputs are unchanged; when they did change, give
the judgement the stored rating plus the input delta and require a changed rating
to name the change it rests on. Per-criterion request partitioning was
**considered and rejected** — under carry-forward an unchanged criterion is never
sent to the model at all. The issue records why, so it need not be re-litigated.

## Filed this session

**#244** (fixed and merged), **#248**, **#249**, **#250**, **#251**, **#252**,
**#253**, **#254**. All attached to their umbrellas.

## Do not rediscover

- **A prompt change invalidates only THAT STAGE's transcripts**, not the whole
  cache — `request_key` hashes each request individually. CLAUDE.md said
  otherwise until this session and the wrong reading had already cost one lane a
  near-unnecessary serialisation.
- **`git branch -d` refuses every squash-merged branch.** The branch commits
  never enter main's history. Confirm via `gh pr view <n> --json state` and then
  `-D`; do not assume the refusal means unmerged work.
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

## Parallel lanes — what worked

Worktrees under `~/acceptance-worktrees/`, outside Google Drive, one `.venv`
each, each driven from a session whose cwd is that worktree. Conditions that held
and should hold again:

- **At most one lane may touch a model prompt.** #244 was that lane; the other
  two touched none.
- **Rebase early.** Both later lanes conflicted only in `current-task.md` and
  `session-state.md`, which every lane rewrites wholesale.
- **Lanes should tell each other what moved.** #214's handover naming the exact
  regions it had changed in `pipeline.py` and `review_state.py` made #244's
  rebase a single trivial conflict.
