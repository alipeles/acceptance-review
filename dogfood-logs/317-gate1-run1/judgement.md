# Judgement — #317 Gate 1, run 1

*Run at `a10cdc0` on branch `317-disposition-union`, 2026-08-21.*

```
.venv/bin/acceptance decompose --task current-task.md
```

Exit 0. Run id `b1c236b5709e2768`. 22 requirements, 21 with obligations, 1
deliberately none, 3 decompose calls. No open questions.

`output.log` came back **zero bytes with exit 0** on the first attempt. The
identical command after `rm -f` produced the full 8.1 KB. That is the failure
CLAUDE.md already documents and has no known cause; recorded here as another
instance.

## Coverage: complete

Every one of the seven Constraints, five Scope exclusions and nine Completion
expectations is accounted for. Nothing in the mandate went unread. `Implementation.`
is disposed as deliberately yielding no obligation — "Section marker only; it
names no checkable requirement by itself" — which is right.

## Two problems, both in obligations derived from the Task paragraph

**1. A duplicate obligation, unmerged.** `task-01` yielded
`combine-agreeing-accounts-2`, which states the same property as
`constraint-01`'s `combine-agreeing-accounts`. The `-2` suffix is `_unique`
renaming a collision, so the decomposer generated the **same identifier** for
both — the strongest available signal that they are the same obligation — and
the linking stage still did not merge them. The linker was not idle: it merged
`task-01`'s `stop-on-disagreeing-outcomes` with `constraint-05`'s correctly, and
labelled it "(also serves constraint-05)". So one merge landed and one did not,
in the same run.

**2. A redundant third obligation.** `repetition-does-not-stop-review` restates
`combine-agreeing-accounts` from the negative side. It comes from the Task
paragraph's second sentence, which was a gloss on the constraints rather than an
independent requirement.

**3. A scope exclusion derived into a malformed prohibition.** `exclusion-01`
read "Whether an answer the review cannot read should stop the whole review or
only the requirements that answer was asked about", and yielded:

> The review does not let an unreadable answer stop the whole review **or only
> the requirements that answer was asked about.**

That is not a coherent property — it asserts the review does neither of two
exhaustive alternatives. The requirement was phrased as a "whether A or B"
question rather than a noun phrase naming a topic; the four other exclusions,
all noun phrases, yielded sane obligations.

## Disposition

Problems 2 and 3 are **my wording**, and both are the sanctioned rewrite of a
weak obligation. `current-task.md` was rewritten to (a) drop the Task
paragraph's restatement of the constraints, and (b) make `exclusion-01` a noun
phrase like its neighbours. Re-run as run 2 with
`--continue b1c236b5709e2768`, per the gate's rule that a correction re-arms it.

Problem 1 is a tool finding and is carried into run 2's judgement, where it
reproduces after the wording that could have explained it is gone.

## No open questions is not a clean bill

Zero were raised. That is not evidence the mandate is unambiguous: **#303** —
decomposition cannot raise an open question about a requirement that also yields
obligations, and has raised none since #217 — means this stage is structurally
incapable of raising one here. The gate's open-question triage therefore has
nothing to work with, and its silence should not be read as a pass.
