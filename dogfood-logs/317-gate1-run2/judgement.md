# Judgement — #317 Gate 1, run 2 — **superseded by run 3**

> **This run did NOT pass Gate 1, and this file said it did.** Re-reading the
> breakdown below found a contradiction in the mandate that this judgement
> missed: `disambiguate-colliding-obligation-identifiers` (constraint-03) and
> `stop-on-differently-stated-shared-obligation` (constraint-06) demand opposite
> things about the same mechanical condition — two obligations sharing an
> identifier. The second was also scope invented beyond issue #317. Both bullets
> were removed and the gate re-armed; `dogfood-logs/317-gate1-run3/` is where
> Gate 1 actually passes. The findings recorded below about the two tool defects
> are unaffected and still stand.

*Run at `a10cdc0` on branch `317-disposition-union`, 2026-08-21, after the
wording fixes run 1 called for.*

```
.venv/bin/acceptance decompose --task current-task.md --continue b1c236b5709e2768
```

Exit 0. Run id `b35e72704d1fc4f9`, continuing `b1c236b5709e2768`.
**0 derived, 20 carried, 2 revised, 1 decompose call** — down from 3. The two
revised requirements are exactly the two I reworded. Carry did what #269 built
it to do: twenty untouched requirements did not move, and were not paid for.

`output.log` came back zero bytes with exit 0 again, and the identical command
after `rm -f` produced 8.0 KB. Second instance in two runs this session.

## What the rewording fixed

`repetition-does-not-stop-review` is gone. It was a negative restatement of
`combine-agreeing-accounts`, produced from a Task sentence that glossed the
constraints; removing the gloss removed the obligation. `task-01` now yields two
obligations instead of three.

## What the rewording did NOT fix — two tool findings

**1. The duplicate obligation survives, and now cannot be blamed on my wording.**
`task-01` still yields `combine-agreeing-accounts-2`, described as "When several
accounts of one requirement agree on that requirement's outcome, the review
combines them into one account and carries on" — the same property as
`constraint-01`'s `combine-agreeing-accounts`.

This is sharper than it was in run 1. My Task paragraph no longer states that
property at all; it now reads "What the review does with such an answer turns on
whether those accounts agree with one another", which names the *topic*. The
decomposer manufactured a full restatement of `constraint-01` from it, the
generated identifier collided (hence `-2`), and the linker still did not merge
them — while merging `disagreement-stops-review` across `task-01` and
`constraint-05` in the same run, correctly labelled "(also serves constraint-05)".

An identical generated id is the strongest twin signal available and it is not
being used. **Attribution:** the twin-splitting family — #304, #242, and the
open blocker already in `docs/DEFERRED.md` ("Unmerged twin obligations
measurably starve each other of mapped tests"). Recorded as an instance against
that item; not re-filed.

**2. A reworded scope exclusion re-derived onto its old, false obligation.**
`exclusion-01` was rewritten from a "whether A or B" question into the noun
phrase "How much of a review an answer the review cannot read at all stops." It
was one of the two requirements the run re-derived — its obligation `type` moved
from `functional` to `compatibility`, so the model was asked again — and the
description came back **byte-identical to run 1's**:

> The review does not let an unreadable answer stop the whole review or only the
> requirements that answer was asked about.

That sentence is still incoherent, and it no longer corresponds to any text in
the mandate. **Attribution:** the queued item "[2026-08-20] A reworded scope
exclusion is re-derived from the new text and lands on the old, false
obligation". This is a clean reproduction of it — same shape, different mandate.
Recorded as an instance; not re-filed.

Neither finding is fixable by further rewording, and chasing them with a third
rewrite would be working around a tool defect, which the gate forbids.

## Is this a breakdown I would defend? Yes, with those two exceptions named

- **Nothing real is missing.** All seven Constraints, five Scope exclusions and
  nine Completion expectations are represented.
- **The seven obligations that define the work are accurate and well-formed** —
  `combine-agreeing-accounts`, `preserve-all-obligations-in-combined-account`,
  `disambiguate-colliding-obligation-identifiers`,
  `record-that-combining-happened`, `disagreement-stops-review`,
  `stop-on-differently-stated-shared-obligation`, `single-account-unaffected`.
  Each is a faithful restatement of its constraint, correctly typed.
- **Two obligations are wrong**: one duplicate that should have merged, one
  malformed prohibition. Both are known tool defects with queue items, and
  neither touches the obligations that describe what is to be built.

## Open questions: none, and that means nothing here

Zero raised, as in run 1. Per **#303**, decomposition cannot raise an open
question about a requirement that also yields obligations and has raised none
since #217, so this stage could not have raised one. The three-case triage in
the gate's table has nothing to apply to. Silence here is a known blind spot,
not a clean bill.
