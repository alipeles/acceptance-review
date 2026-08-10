# Session state

Rolling state for the task in flight. Keep the headings; rewrite the contents
wholesale rather than appending. Update before stopping, and any time losing the
last hour would hurt.

Committed, so it survives a context reset or a machine change — but still a
scratch record, not a plan. **The GitHub issue stays authoritative** (#168).
Clear it out when the task lands rather than letting it accrete.

*Last updated: 2026-08-10*

---

## In flight: #248 — a repeated obligation is read as one

Branch `248-drop-duplicate-obligations`, off `4619e78`. Child of #181, picked up
because decomposition quality sequences ahead of evidence judgement.

**Gate 1 run three times**, all committed under `dogfood-logs/248-gate1-run{1,2,3}/`.
**Run 3 is the accepted one**; agent confirms the breakdown, **human confirmation
pending**. If the next session finds this line unchanged, the gate never closed.

- Run 1: decomposition accurate, but written to the wrong mandate — see below.
- Run 2: **rejected.** `task-01` was given `exclusion-06`'s obligation and lost
  its own (#223). Also over-split two compound constraints of mine into
  near-identical obligations.
- Run 3: 27 requirements, 26 yielded, every one exactly one obligation quoting
  it, **no unreconciled cluster**, no open questions.

## The finding that changed the design — do not re-derive this

#248 as filed says the model emits one requirement's obligation twice and
prescribes dropping an obligation whose *description* repeats. **That is wrong,
and building to it would have been wallpaper.** The human caught it; transcript
evidence settled it.

Scanned all 1,055 recorded transcripts: **4** duplicate-bearing dispositions,
**all four** byte-identical `obligation` vs `more_obligations[0]` — same
description, same `id`, same `type`, same `source_quote` — every one with
`len(more_obligations) == 1`, and **zero** duplicates in any other position. In
the same response, requirements yielding 2 and 3 obligations showed no
duplication at all.

So the duplicate is **schema-induced**, and specifically induced by the fix for
**#217**: `_Yielded` splits the list into a required `obligation` plus
`more_obligations` because strict mode rejects `minItems`, and that split is the
only way to make "at least one" structural. The two fields have no stated
relationship and the prompt never mentions them, so in the **one-obligation
case** the model fills the required slot and then emits the same object again as
the whole list — a defensible reading of what it was handed.

**Head+rest is the only structural non-empty encoding available**, so the
ambiguity is inherent to the shape. No schema edit can eliminate the case; it can
only make it rarer. The decoder guard is therefore the real fix, not a patch over
one.

The scan script is disposable but worth rewriting if needed:
`scratchpad/scan_dupes.py`, classifying each duplicate as head-vs-`[0]`,
head-repeated-later, or internal-to-remainder.

## The plan

One change, in `src/acceptance/requirement/obligations.py`:
`_Yielded.derived()` returns the head plus the remainder **with a byte-identical
echo of the head dropped at position 0 only**. Record it on `UnusableAnswerLog`
with a reason naming the response shape, not a faulty answer.

- **Position 0 only**, deliberately. A repeat later in the list would be the
  model genuinely restating itself — linking's call — and a guard that drops
  repeats anywhere destroys the signal that something upstream is wrong.
- **Whole-object equality**, not description matching. The exact-vs-normalised
  question in the issue is withdrawn; it does not arise.
- `_Yielded` structurally carries at least one obligation and the head always
  survives, so "never left holding none" holds by construction.
- **No request changes, so nothing re-records** and benchmark figures stay
  comparable. This is why the fix is cheap.
- Needs a test that `decompose` actually routes through the guard, not only a
  unit test of the helper (the wiring hole `CLAUDE.md` warns about).

## Queued, awaiting the gate — see `docs/DEFERRED.md`

1. **decision** — rename `_Yielded`'s fields and add a prompt sentence, to be
   spent at the next change that already forces a decompose re-record. Approved
   in principle by the human this session; the entry records that the decoder
   guard stays regardless.
2. **filing** — correct #248's Deliverable and Acceptance, which are
   mis-specified as description-comparison dedup.
3. **filing** — comment on #223 with run 2's destroyed headline requirement.
4. **filing** — comment on #242 with run 1's unreconciled cluster.

## Do not rediscover

- **A prompt change invalidates only THAT STAGE's transcripts**, not the whole
  cache — `request_key` hashes each request individually.
- **`git branch -d` refuses every squash-merged branch.** Confirm via
  `gh pr view <n> --json state` then `-D`.
- **`git stash` mid-task reverts the working tree wholesale.** Use a second
  worktree or `git show` to inspect a baseline instead.
- **A `check` over a new task file needs `--mode record`** and makes live calls.
- **`.acceptance/ignore` is committed** (#105) and holds `dogfood-logs/`.
- **`decompose|check --mode record` writes nothing to stdout when redirected** —
  pipe through `tee`.
- **Compound constraints get over-split.** Run 2 proved it: one constraint
  joining two statements with "so" yielded three near-identical obligations, and
  splitting it into single-statement constraints fixed it. Write one statement
  per bullet in `current-task.md`.
- **A `PostToolUse` formatter hook reformats files after every edit.**
- **Obligation ids are minted per response, not stable across runs** (#231).
- **Python here is 3.10; CI runs 3.12**; repo is `alipeles/acceptance-review`.

## Where the rest of the queue stands

**#180's split** — #251, #252, #253, #254 — stays parked behind #181; each judges
an obligation set that is not trustworthy yet. #251's design is settled and was
the human's; see the issue.

**The open empirical question** before designing #251: how much of #180's
measured churn was decomposition redundancy rather than judgement variance.
Runs 1–3 here are three more data points that it is substantially decomposition:
the same mandate, reworded, moved between 24 and 27 requirements and between one
and three obligations per requirement.
