# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed to `main` at the gates, never to the branch under review (see
`CLAUDE.md` *Working conventions*) — but still a scratch record, not a plan.
**The GitHub issue stays authoritative** (#168). Clear it out when the task lands
rather than letting it accrete.

*Last updated: 2026-08-11*

---

## No task in flight

**#248 landed** — `aef2191` (PR #257), CI green. A one-obligation response that
echoes the required `obligation` field into `more_obligations` is now read as one
obligation, not two.

**`current-task.md` is stale** — it still holds #248's mandate, which has
shipped. Ignore it; the next task writes its own at Gate 1.

## What #248 changed about how we read defect reports

Worth carrying forward, because the issue as filed was wrong and building to it
would have made things worse:

- The duplicate was **schema-induced**, not the model repeating itself. `_Yielded`
  splits the list into a required `obligation` plus `more_obligations` because
  strict mode rejects `minItems` (#217), the two fields' relationship is stated
  nowhere, and in the one-obligation case the model fills the slot and repeats
  it as the whole list. **The fix for #217 caused it.**
- Evidence: all 1,055 transcripts scanned — 4 duplicate-bearing dispositions,
  every one byte-identical head vs `more_obligations[0]` with a
  single-entry remainder, zero anywhere else.
- #248 originally prescribed dropping obligations with duplicate *descriptions*.
  Defect injection proved that wrong: 4 of 5 parametrised cases collapse
  distinct obligations under it.
- **#256** carries the follow-up — rename the fields, add a prompt sentence —
  deferred until something else already forces a decompose re-record. The
  decoder guard stays load-bearing when it lands; do not remove it.

## Gate 2 could not be made clean, and that is filed

#248's Gate 2 stayed INCOMPLETE. Two tests were added and nothing removed; one
obligation improved and **eleven untouched ones fell** from strongly to partially
supported. Three recommendations made checkably false claims about the code, one
prescribing a test for the negation of a requirement the same report rated
satisfied. Filed on **#225** with both runs committed under
`dogfood-logs/248-gate2-run{1,2}/`. The human chose to merge on the strength of
four defect injections rather than chase the rating.

**This is the strongest argument yet for taking #225/#180 seriously before more
capability work**: a gate that moves under unchanged evidence cannot validate
anything downstream.

## Next up

`CLAUDE.md`'s sequencing rule still points at **#181**. The remaining
decomposition defects, in the order the evidence supports:

- **#223** — a spurious link that *completed*, destroying the headline
  requirement's obligation. Fresh evidence added this session from
  `dogfood-logs/248-gate1-run2/`.
- **#242** — the same similarity judgement failing the other way: a spurious
  link that *blocks*, so an inconsistent cluster merges nothing.
- **#210** — over-merging.

**These three may want one fix rather than three** — that is noted on #223 and
#242 and is worth settling before starting any of them. Blocking is the loud,
safe failure; completing is silent and leaves a plausible-looking breakdown.

**#180's split** (#251–#254) stays parked behind #181: each judges an obligation
set that is not trustworthy yet. #251's design is settled and was the human's.

## Queued — see `docs/DEFERRED.md`

One open item: untracking `current-task.md`, **blocked on #258** (two tests read
the live file; #258 repoints them at the committed dogfood corpus). Do #258
first, then untrack.

## Do not rediscover

- **A prompt change invalidates only THAT STAGE's transcripts**, not the whole
  cache — `request_key` hashes each request individually.
- **`git branch -d` refuses every squash-merged branch.** Confirm via
  `gh pr view <n> --json state` then `-D`.
- **`git stash` mid-task reverts the working tree wholesale.** Use a second
  worktree or `git show` to inspect a baseline instead.
- **A `check` over a new task file needs `--mode record`** and makes live calls.
- **`decompose|check --mode record` writes nothing to stdout when redirected** —
  pipe through `tee`, and **never `tee | head`**: the SIGPIPE truncates the log
  to zero bytes. Two Gate 1 logs were committed empty this way before the PR
  diff caught it. Check `wc -l` on the log before trusting it.
- **A dogfood log lost to that can be rebuilt by replay** against its committed
  task file — same transcripts, no live calls, byte-identical output. That is
  determinism paying off; say in the judgement that it was regenerated.
- **Compound constraints get over-split.** One constraint joining two statements
  with "so" yielded three near-identical obligations; splitting it fixed it.
  Write one statement per bullet in `current-task.md`.
- **A `PostToolUse` formatter hook reformats files after every edit.**
- **Obligation ids are minted per response, not stable across runs** (#231).
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.
