# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## In flight: #244, at Gate 2, not clean

**#244** — *an obligation's `source_quote` is not checked against the requirement
it is attached to* — filed this session as a child of **#181**. Branch
`180-evidence-rating-stability`, rebased onto `75fefc4`, two commits:
`3471623` (the fix) and `dd4caf5` (one test added in response to Gate 2 run 1).

Gate 1 passed at `0923f77`; re-armed after the mandate changed and passed again
with one queued defect. Gate 2 ran twice and is **not clean** — INCOMPLETE both
times, two obligations below strongly supported, neither an unmet requirement.
Full analysis in `dogfood-logs/244-gate2-run2/judgement.md`. Awaiting a human
call on whether to open the PR.

Full suite green on the rebased tree: **1048 passed**. Ruff clean.

## Why this lane is on #244 and not #180

Assigned #180 (rating stability). Its Gate 1 failed: a one-sentence Task
requirement produced **seven** obligations, three paraphrasing it and three
carrying other requirements' content, which the linking stage reported as
unreconcilable. Deleting a redundant seven-word clause took it from 2 obligations
to 7. Reproducible — a repeat run was byte-identical.

Human call: fix decomposition first. #180's own Gate 1 became the evidence for
#244, and the split of #180 into four children is still queued, unfiled.

## What #244 changed

`_locate_quotation` + `_resolve_attributions` in `requirement/obligations.py`.
Two things the issue did not anticipate, both found by the tests:

- **Matching ignores line breaks.** Task prose is hard-wrapped, bullets are not,
  so one sentence appears wrapped in one requirement and flat in another. Exact
  substring matching found it only in the unwrapped one — on the linking corpus
  that moved the Task prose's obligation onto the constraint restating it,
  deleting the cross-section duplicate that corpus exists to exercise.
- **Nothing is discarded, and re-filing never empties a requirement.**
  `_requirement_map` raises when a `yielded` requirement carries none, so moving
  a requirement's last obligation turns a quoting slip into a failed review.

The second forced a **mandate change mid-implementation** — `current-task.md`
originally said an unplaceable obligation is dropped. Disclosed as a design
change, not a wording fix; see `dogfood-logs/244-gate1-run2/judgement.md`.

## Gate 2's two findings, both attributed to tool defects

1. **A recommendation asks for the test it is already citing.** Run 1's finding
   was real, I wrote the test, run 2 maps and cites it — then recommends it
   again. #183.
2. **`tests-issue-no-live-model-calls` lost its whole mapped set**, two tests →
   zero, between runs that did not touch it. #182. **Independently reproduces
   the #214 lane's finding on the same obligation** (`issuecomment-5245416368`).

Both queued in `docs/DEFERRED.md`; neither filed.

## Parallel lanes — both finished

**#214** merged as `7573697`, **#228** as `75fefc4`. This lane is the only one
left. Two things #214 handed over that are worth keeping:

- Open-question resolution moved in `pipeline.py`: it now runs immediately after
  `link_duplicate_obligations`, before `discover_tests`, not after the evidence
  stages.
- Derived obligations from resolved questions get ids computed in code from the
  question id, so they are stable across runs by construction.

## Queue — `docs/DEFERRED.md`

Five open, none filed: the #180 four-way split, the duplicate-obligation defect,
the mapping miss, the recommendation restatement, and the DR-164 revisit (now
moot — recommend dropping).

Filed this session: **#244**.

## Do not rediscover

- **A prompt change invalidates only THAT STAGE's transcripts**, not the whole
  cache — `request_key` hashes each request individually. CLAUDE.md said
  otherwise and was corrected this session; it had already cost the #214 lane a
  near-unnecessary serialisation.
- **`git stash` mid-task reverts the working tree wholesale.** Used it to check a
  baseline and lost the tree until `stash pop`. Use a second worktree or
  `git show` instead.
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

## Known open

**#210**, **#180**, **#193**, **#191**, **#196**, **#178**, **#129**, **#223**,
**#224**, **#173**, **#225**, **#227**, **#212**, **#231**, **#236**, **#237**,
**#239**, **#244**.
