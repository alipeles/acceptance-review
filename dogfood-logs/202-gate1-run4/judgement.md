# Judgement — #202 Gate 1, run 4

Same `current-task.md`, byte-identical across all four runs. Run after fixing a
regression this change had introduced.

## What changed since run 3

**`parse_task_file` kept only the first paragraph under `# Task`.** My task file
has four. The one kept was the *problem statement*; the three dropped included
the mandate sentence — *"Make decomposition return a mapping from requirement to
obligation…"*.

That gap was harmless for as long as `_user_prompt` handed the model
`parsed.source` and it read the file itself. **M1.2.r1 made it fatal**: once the
registry became the only thing the model sees, unparsed text stopped reaching it
at all. The change introduced silent data loss, and its first casualty was three
paragraphs of its own mandate.

Fixed here, with a guard: every content block the parse does not claim is
recorded as `unread_source` and rendered loudly by both the CLI and the §16
report. The structured-interchange invariant has a precondition nothing was
checking — **a parse may only be authoritative if it reports what it missed.**

## Head-to-head

| | run 1 | run 2 | run 3 | run 4 |
|---|---|---|---|---|
| requirements identified | — | 44 | 44 | **47** |
| with obligations | 30 of 42 | 35 | 43 | **46** |
| deliberately none | — | 9 | 1 | 1 |
| unaccounted | n/a | 0 | 0 | **0** |
| unread source blocks | not detectable | not detectable | not detectable | **0** |

47 = 44 + the three Task paragraphs that had been invisible. The single decline
remains `completion-01: Implementation`, correctly.

## Finding 1 — the contradiction is gone, and not for the reason we expected

Runs 1–3 all produced an obligation to **preserve the flat list** — the thing
being removed — derived from the problem statement, sitting alongside the
obligation to replace it.

Run 4 does not. `task-01` is the same paragraph, and it now maps to
`obligation-requirement-to-obligation-mapping` and
`obligation-record-none-disposition`, both shared with `task-02`.

**The cause was not context bleed.** It was the missing mandate. Given the
problem statement alone and told to account for it, the only reading available
was "this describes what the tool does, so it is a requirement." Given the very
next paragraph too, the model correctly subordinates the problem statement to the
mandate it motivates.

This matters for **#212** (the `## Context` section), which was filed with this
contradiction as its motivating example. That example no longer holds and #212's
body has been corrected. The issue is still worth doing — a problem statement
arguably should yield no obligation at all rather than sharing its successor's —
but its evidence is now weaker than when filed, and it should not be built on the
strength of a defect that turned out to be something else.

## Finding 2 — #210's false links persist, and they MOVED

This is the important result, and it is bad news for fixing by inspection.

| requirement | run 3 link | run 4 link | |
|---|---|---|---|
| `exclusion-08` don't align ids across versions | the *within-version* stability obligation | **its own correct obligation** — *"Keep requirement ids from being aligned across two versions of a task file."* | **fixed** |
| `exclusion-09` don't rebuild #195's suite | "the suite runs unchanged" | *"…running against the new output **without rebinding its labels to the mapping**"* | **improved to correct** |
| `exclusion-10` don't measure recall | the *non-comparable annotation* obligation | `obligation-no-semantic-deduplication`, **shared with `exclusion-07`** | **worse** — de-duplication is unrelated to measurement |
| `task-01` problem statement | — | `obligation-regression-suite-195-results-unchanged` | **new false link** — driven by the string `#195` appearing in the paragraph |

Two clear false links in run 4 against two in run 3 — **but not the same two**.
The defect count is flat while its membership turned over almost completely.

`task-01`'s new link is the #210 signal reproducing exactly: the paragraph
mentions *"#195's Gate 1 lost 4 of 15 Completion expectations"*, and the link
lands on the obligation about #195's regression suite. Lexical adjacency, not
shared content.

**Consequence.** #210 cannot be fixed or verified by looking at a run. A change
that "fixed" `exclusion-08` here did not target it, and `exclusion-10` regressed
without anything touching it. This is #193's instability, now visible one level
up in the mapping — and it converts #211 from a good idea into a hard
prerequisite. Recorded on #210.

## Finding 3 — the obligation set is not stable across the change

35 distinct obligations in both run 3 and run 4; **4 ids in common.** The set
turned over almost entirely.

Expected, and not alarming on its own: the prompt changed and the model now sees
three paragraphs it never saw before. But it is worth stating plainly that
**#202 is no longer purely representational.** Its task file says so
(`exclusion-01`, *"Changing which obligations a task file decomposes into"*), and
that is now violated — necessarily, because the alternative was shipping a change
that hides part of the mandate from the model.

The right disposition is to say so rather than to claim the exclusion held.
#195's control suite still passes and no case flipped, which is the check that
matters — those cases score the decomposer against fixed ground truth, and they
are unaffected.

## Finding 4 — the guard reports nothing, which is the correct answer here

`unread_source` is empty for this file: every block sits under a recognised
heading. Zero is printed rather than omitted, because an absent line is not an
assurance. The tests cover the non-empty case with a `## Background` section and
with a markdown table — the latter because #195's own task file carries its
ground truth in tables, which this parse has never read and now says so.

## Disposition

| finding | disposition |
|---|---|
| 1 — contradiction resolved by the parse fix | delivered; **#212's motivating example corrected** |
| 2 — false links persist and move | recorded on **#210**; hardens **#211** into a prerequisite |
| 3 — obligation set turned over | disclosed, not excused. `exclusion-01` of this task file is violated |
| 4 — unread guard | delivered |

`current-task.md` is unedited across all four runs.
