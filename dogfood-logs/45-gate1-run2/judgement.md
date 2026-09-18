# Judgement — #45 Gate 1, run 2

Run id `cdbfa65e8bf73901`, continuing `c4e3938a331d4d36`. 12 requirements, 22
obligations, zero open questions.

**Not accepted, but close.** Both of run 1's problems are gone. The carry worked:
8 requirements carried, 3 revised, 1 derived, and the run reported
`REMOVED task-01` (3 obligations dropped) and `REMOVED constraint-03`
(1 obligation dropped), which is exactly the two edits made to the task file.

One new problem, which run 3 then failed to fix.

## The remaining problem

`task-04`'s last sentence was "A review where nothing can be run reaches the
conclusions it reaches today, with its evidence recorded at the weaker tier." It
produced two obligations:

- `review-conclusions-unchanged-when-unrunnable` — *"A review where nothing can
  be run reaches the conclusions it reaches today."* Keeps the condition.
- `weaker-tier-evidence-recorded` — *"The review records its evidence at the
  weaker tier."* Drops it.

The second, read alone, says every review records at the weaker tier. That
directly contradicts `recorded-at-strongest-evidence-tier` under `task-01`. Two
obligations in the same set now demand opposite things, and a judge evaluating
either in isolation reaches the wrong answer about a correct implementation.

Attempted fix in run 3: rebind the condition to the front of the sentence
("Where nothing can be run, the review reaches the conclusions it reaches today
and its evidence stays at the weaker tier"). It did not work — see run 3.

## Cost

$0.0669 recorded, 15 calls.
