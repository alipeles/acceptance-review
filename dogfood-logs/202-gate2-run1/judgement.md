# Judgement — #202 Gate 2, run 1

`acceptance check --task current-task.md --base 4ec4470 --head d90eb51`.
Revisions pinned in `revisions.txt`.

**Verdict: INCOMPLETE. Gate 2 is NOT clean, and this is a stop.**

Clean requires every obligation addressed, every obligation strongly supported,
every open question resolved, no recommended tests, and no other flag. This run
has 4 coverage gaps, 8 recommended tests and 7 unsupported obligations. Not a
threshold to negotiate.

## Mapping audit first (DR-164)

**28 of 35 obligations carry at least one mapped test — 80%.** This is not the
half-blind failure DR-164 records at ~17%, so the findings below are believable
rather than artifacts of a mapping that never happened.

(The raw transcript count is useless here: `.acceptance/cache/` holds 144 mapping
transcripts accumulated across every run this repo has ever made, and pooling
them reads 45%. Measure from the persisted review, not the cache.)

## The headline: the tool caught what I had already disclosed

Two of the four coverage gaps are the same finding:

> *The change is explicitly framed as representational and the obligation content
> is intended to stay fixed, but the diff also changes parsing, prompt shape, and
> report structure, so the invariant is only partly upheld.*

That is **correct**, and it is the violation I recorded in run 4's judgement
before this ran: 35 obligations in runs 3 and 4 with 4 ids in common. The tool
reached it independently, from the diff, without access to my judgement files.

It found it a **second** time on the other axis, as unrequested changes:

| # | disposition | what it says |
|---|---|---|
| 10 | `in_service` | *"parse_task_file now records every paragraph, unclaimed blocks… do not require broadening parse_task_file to capture unread source or changing behavior extraction from a single span to a list"* |
| 14 | **`separable`** | *"The task-file tests now assert multi-paragraph behavior, unclaimed text, and table handling."* |

Both correct. **The parse fix and the unread guard are genuinely outside #202's
mandate.** I did that work because it was a regression this change introduced,
and I still think that was right — but the task file never asked for it, and the
tool is right to say so.

This is the strongest positive result the tool has produced against its own
development so far: a real, non-obvious scope finding that a careful reviewer
would raise, arrived at independently and labelled correctly on both axes.

**No disposition is available to me here.** It is neither a tool defect nor
something to fix by editing `current-task.md` — adding the parse fix as a
requirement to silence the finding is precisely the prohibited edit. It needs a
human decision (below).

## The rest of the gaps

**`obligation-transcripts-rerecorded-once`** — *"whether they were re-recorded
exactly once is a process/history fact not provable from code alone."* The tool
is right. **This is my task-file authoring defect**, not a tool defect:
*"Recorded transcripts invalidated by the changed prompt are re-recorded once"*
is a process instruction, not a property of delivered code, and no test can
evidence it.

It is a legitimate candidate for the sanctioned weak-obligation rewrite — I
regret the wording, which is CLAUDE.md's tie-break. **Not rewriting it
unilaterally**, because doing so *after* seeing the finding is the exact shape
the standing invariant warns about. Human decision.

**`obligation-no-base-context-decision`** — from `exclusion-06` (#208). Untestable
negative. #153.

## The recommendations are mostly #153, exactly as predicted

Five of eight ask for a test proving a negative about work deliberately not done:

| # | asks for a test that | from |
|---|---|---|
| 2 | obligation types are **not** assigned in a later pass | `exclusion-03` (#205) |
| 3 | open-question handling does **not** consult the base revision | `exclusion-05` (#207) |
| 4 | this change does **not** decide base-revision context | `exclusion-06` (#208) |
| 5 | duplicate obligations are **not** merged | `exclusion-07` (#144) |
| 6 | ids are **not** reconciled across versions | `exclusion-08` (#209) |

This is **#153** verbatim — *scope exclusions demand test evidence that cannot
exist* — and it is why #190 and #195 never came back clean either. Predicted
before the run, and tracked. No action here.

**Recommendations 7 and 8 are different and worth noting.** They ask for evidence
that #195's suite still runs with its labels and that no case flipped. That
evidence *exists*: the suite is `tests/benchmark/test_decompose_regression.py` and
it passes, which **is** "no case flipped". The tool cannot see that a green
regression suite is itself the evidence for a "nothing regressed" obligation.

That is a genuine tool limitation and it is **not currently tracked**. It belongs
with #183/#185. Candidate for filing — flagged, not filed, pending the human.

## Unrequested changes: 17, and the ratio is the point

15 `in_service`, 2 `separable`. The two separable are `dogfood-logs/` (mandated by
CLAUDE.md, requested by no task file — the known standing case, possibly an input
to #88) and the task-file tests discussed above.

The 15 `in_service` are correctly dispositioned: implementation detail in service
of a stated obligation, presented advisory rather than as gaps. Several are sharp
— #5 correctly notes the CLI renders unread source and orphan obligations which no
obligation asks for; #6 notes `UnusableAnswerLog` threading that nothing required.
All true.

## Predictions made before the run, and how they held

| prediction | outcome |
|---|---|
| #153 caps the scope exclusions | **held** — 5 of 8 recommendations |
| two `separable` unrequested changes, `session-state.md` + `dogfood-logs/` | **half held** — 2 separable, but the second is the task-file tests, not `session-state.md` |
| mapping audit before believing the verdict | **done** — 80%, believable |

Recording the miss rather than quietly adjusting: I expected `session-state.md` to
surface as separable and it did not.

## Disposition

| finding | disposition |
|---|---|
| representational invariant violated (2 gaps + 2 unrequested) | **real, correct, needs a human decision.** Not a tool defect; not editable away |
| `transcripts-rerecorded-once` unprovable | **my authoring defect.** Rewrite candidate, deferred to the human |
| `no-base-context-decision` + 5 recommendations | **#153**, tracked, no action |
| recs 7–8: green suite not read as evidence | **untracked tool limitation.** Candidate for #183/#185 |
| 15 `in_service` unrequested changes | correct, advisory, no action |

## What has to happen next

Gate 2 does not pass, so this does not proceed to a PR as it stands. The decision
that unblocks it is not mine: either the scope growth is accepted and
`current-task.md` was simply an incomplete statement of the work, or the parse fix
and unread guard are split into their own issue and this branch narrows to the
mapping alone.
