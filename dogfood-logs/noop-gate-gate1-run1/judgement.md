# Comment-and-whitespace gate, Gate 1 run 1 — judgement

Run `af4321d0ce826ec8`. Worktree `refuse-comment-only-edits` at `768b0d7`.
$0.0010 live; 11 of 13 calls replayed from an earlier attempt of the same run
that died at obligation linking on a Voyage 401, having already paid $0.0561 to
record the decomposition. Record-if-missing meant none of that was wasted.

**Not accepted.** 7 obligations over 6 requirements, with one requirement
dropped that should not have been and one obligation derived from context.

## The Constraint was dropped, and the reason given is wrong

`constraint-01`, *"No model is asked."*, was dispositioned as yielding no
obligation:

> The requirement explicitly says no model is asked, so it imposes nothing
> checkable on the delivered change.

That is false. "No model is asked" is directly checkable — a test asserts the
model client is never called on this path — and on this task it is the point of
the change rather than an aside. A constraint disposed away is a constraint the
review will never look for.

**Attribution is mixed and I am not certain.** The bare phrasing invites reading
it as a statement about the task rather than about the delivered behaviour, so
the rewrite below is warranted either way. But a decomposer that calls an
unambiguous prohibition "nothing checkable" is not obviously doing its job.

Related, and close enough that this may be the same defect: #353, filed from
#335's Gate 1 the same day, where a plain Constraints prohibition produced an
open question instead of an obligation. Both lose a Constraints prohibition;
they differ only in what they leave behind.

## Context became an obligation

`comments-or-whitespace-only-no-change` — *"An edit that differs from the text it
replaced only in comments or whitespace changes nothing."* That is the rationale
for the requirement, not a thing the software does. **Mine**: the task file's
first sentence stated the reason and the requirement in one breath. Same shape as
#212, task files cannot distinguish context from requirements.

## Disposition

Task file rewritten: the rationale clause dropped from the first sentence, and
the Constraint restated as *"The refusal is reached without asking a model."* —
a property of the delivered behaviour rather than a remark about the task. Run 2
continues this run.

## Ledger check

9 derived, 1 merge, 7 printed, and every derived id accounted for.
