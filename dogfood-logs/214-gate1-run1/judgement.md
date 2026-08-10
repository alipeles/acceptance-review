# Judgement — #214 Gate 1, run 1

Command: `.venv/bin/acceptance decompose --task current-task.md --mode record`
Base SHA: `0923f77` (branch `214-verdict-mandate-coverage`, no commits yet).

## Result

25 requirements, 24 yielded an obligation, 1 deliberately declined, **0 open
questions**, **0 unread source blocks**. Confirmed absent rather than assumed:
`cli.py::_summary` omits the "raised a question" part only when the count is
zero, and `_unread_source` renders nothing only when the list is empty.

## Is the breakdown accurate?

Yes. Every one of the 25 requirements maps to exactly the bullet it came from,
each obligation restates its requirement without inventing a demand, and no
requirement of the mandate is missing. Nothing was invented: there is no
obligation that does not trace to a bullet I wrote.

Two things worth recording.

**The one decline is the case the task is about.** `completion-01` is the bullet
`- Implementation`, declined as *"A standalone section marker with no
requirement under it."* That is precisely the shape #214's Acceptance item 4
demands not be penalised, and it arrived unprompted in this task's own file —
the same bullet #153's file carried. So the fixture for item 4 is not invented
for the test; it is the live behaviour of the decomposer on an ordinary mandate.

**Scope exclusions yielded obligations in absence form, as #153 landed.** All
seven exclusions produced `CODE_ONLY`-shaped obligations ("The change does not
alter ..."), which is the behaviour merged in `0923f77`. `exclusion-01` is
rendered slightly differently from the other six — "The change does not re-judge
whether..." rather than "does not alter" — which is correct: my bullet states a
behaviour to abstain from, not an area to leave untouched.

## Open questions

None raised, so the three-case triage has nothing to classify.

This is worth flagging rather than passing over: a 25-requirement mandate that
raises no question at all is unusual against this repo's recent history. I read
it as a property of the input rather than of the tool — the mandate was written
after the design was settled against the code, so the decisions a question would
have surfaced (what bounds the verdict, what is exempt) were already resolved in
the wording. The two genuinely open points in this task are recorded as a queued
decision and as an issue-accuracy finding, not as tool output, because the tool
had nothing in its input to raise them from.

## Findings against the tool

None. Nothing in this run is attributed to a tool defect, so nothing is queued
on that account.
