# #334 Gate 1, run 4 — judgement

Run `f1594dbe2bba8c92`, continuing `a7f05ec002634926`. 8 live calls, $0.0356.
Branch rebased onto `main` at `fdf8254` first.

**Accepted, subject to the human's confirmation.** 13 obligations over 6
requirements, zero open questions, every derived id printed.

## Why there is a run 4

Gate 1 re-armed. #334's issue body was rewritten on 2026-09-22 to record the
Gate 1 decisions, and it now says a defect where every candidate is refused gets
an outcome saying no usable edit came out of the candidates, not a claim that
the defect cannot be mutated. Run 3's task file said such a defect "is handled
the way a defect no edit could be built for is handled today", which contradicts
that. One sentence of `task-01` was reworded; nothing else changed. The run
reports `5 carried, 1 revised`, which matches.

## What changed in the obligation set

`task-01` went from four obligations to five. `fallback-to-no-edit-built-handling`
was replaced by two:

- `none-of-candidates-could-be-used` — *"When no candidate passes, the review
  says that none of the candidates it asked for could be used."*
- `preserve-no-edit-built-fallback-handling` — *"Preserve the review's handling
  of a defect when no edit could be built for today."*

Both are real. The first is the new outcome; the second keeps such a defect
routed to the static judge exactly as today.

## Two descriptions lost detail, as on earlier runs

The first dropped the contrast *"rather than that the defect cannot be turned
into an edit"*, which is what makes it a new outcome rather than a relabelled
`not_mutable`. The second reads awkwardly, having lost "when no candidate passes"
as its condition. Same shape as the dropped "always" on the comment-and-whitespace
gate's Gate 1 run 2. Neither is wrong enough to reword again; the test for the
first must assert the outcome is distinct from `not_mutable`, and that is the
thing to check at Gate 2.

## Ledger check

Every derived obligation id appears in the printed breakdown.
