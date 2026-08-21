# Judgement — #302 Gate 1, run 2 (`e5c2490c4a564ea5`, continuing `21f0671ad55f65d1`)

Re-run after reworking two requirements flagged in run 1. **Gate 1 not passed.**

`--continue` behaved exactly as #269 specifies: **0 derived, 17 carried, 2
revised, 1 decompose call.** Only the two reworded requirements moved; the other
seventeen are byte-carried, so nothing below is confounded by unrelated drift.

## What was reworded, and what it did

| requirement | run 1 | run 2 |
|---|---|---|
| `task-01` | *"Every call one stage makes during a review run declares the same answer format, so that what differs between those calls is only which items they ask about."* | *"Keep each stage's answer format the same across a review run, so that a provider able to reuse a repeated request is offered one."* |
| `exclusion-04` | *"Whether a provider reuses any part of a request it was offered, which is the provider's own behavior and not this tool's."* | *"Any guarantee about what a provider does with a request it was offered. Whether it reuses one is the provider's own behavior, which this work neither promises nor prevents."* |

### Fixed by the rewording

The run-1 obligation `only-items-vary-between-stage-calls` is gone. The headline's
purpose clause now yields `provider-can-reuse-repeated-request` — *"A provider
able to reuse a repeated request is offered one"* — which is a fair and accurate
statement of what the software must do, and is accepted.

### NOT fixed — and on inspection, MY ERROR, not the tool's

**Finding A — a Scope exclusion becomes a compatibility obligation that
contradicts the mandate.** `exclusion-04` still yields:

> `does-not-change-provider-request-reuse-behavior` [compatibility/explicit]
> The change does not alter whether a provider reuses any part of a request it
> was offered.

**Initially attributed to the tool, and that attribution was wrong.** Reading
`obligations.py:216-246` settles it. The prompt's contract for the section is
explicit:

> A `## Scope exclusions` section names **work this change must NOT do**. Every
> bullet under it is `yielded`, and produces EXACTLY ONE obligation stating the
> ABSENCE of the excluded work.

and it names this exact error as one of the two wrong forms it warns against
(`:232-236`): *"WRONG — the excluded work asserted as a property to hold."* It
then explains why the section cannot accept one (`:242-246`): a scope exclusion
names WORK, and work has no positive form.

`exclusion-04` does not name work. It is a disclaimer about a guarantee — "we do
not promise what the provider does" — filed under a heading contracted to hold
work. The decomposer did exactly what it is documented to do; the bullet was in
the wrong place. The rewording to "neither promises nor prevents" could not have
helped, because the problem was never the phrasing.

**Fix: delete `exclusion-04`.** What it was trying to say is not a requirement at
all. Nothing else in the mandate promises provider behavior — `task-01`'s
`provider-can-reuse-repeated-request` is about what this tool *offers*, which is
checkable here — so with the bullet gone there is nothing to disclaim.

The same wrong-form bullet appears in #265's task file, unchanged, and should be
expected to have produced the same obligation there.

`exclusion-01`'s trailing sentence — *"This work changes how answers are carried
and identified, not what is asked or decided"* — is the same category of mistake
in milder form: commentary rather than excluded work, and it yielded a second,
redundant `[functional]` obligation. Trimmed in run 3.

This is not merely redundant, it is **self-contradictory within the same run**.
The breakdown simultaneously holds:

- `provider-can-reuse-repeated-request` — a provider able to reuse a repeated
  request **is offered one** (from `task-01`);
- `does-not-change-provider-request-reuse-behavior` — the change **does not
  alter** whether a provider reuses part of a request (from `exclusion-04`).

No implementation can satisfy both. Every downstream stage judges this obligation
set, so the contradiction would be carried into mapping, coverage and the verdict.

**Finding B — two obligations state the same demand and did not merge.**

- `task-01` → `same-answer-format-per-stage-call`: *"Every call a stage makes
  within one review run declares the same answer format."*
- `constraint-01` → `same-answer-format-within-run`: *"Every call a stage makes
  within one run declares the same answer format, whatever items that particular
  call asks about."*

These say the same thing. The tool demonstrably *can* merge a Task/Constraint
pair — #265's Gate 1 run 3 merged `task-01` with `constraint-05` into one shared
obligation — so a non-merge here is a behavior change, not a missing capability.
This is the duplicate-obligation shape tracked under #181.

Not fixed by rewording, and I decline to fix it by deleting `constraint-01`: it
is a real constraint, and removing a genuine requirement to move the tool's
output is editing the input to change what the review says.

## Open questions

**None raised, in either run — and that is not a positive signal.** Per #303,
decomposition cannot raise an open question about a requirement that also yields
obligations, and has raised none since 2026-08-06. The axis reported nothing; it
did not report that the mandate is unambiguous.

## Not new

The `unknown` stage row in the usage table is **#296**, already filed —
`plan_carry` reaching into `benchmark/alignment.py`. Expected on a `--continue`
run.

## Cost

1 decompose call + 1 obligation-linking call + 1 `unknown`, $0.0048 recorded.

`output.log` was again written **zero-byte on the first attempt** with exit 0;
removed and re-run, producing 7,161 bytes. Second occurrence this gate, fourth
recorded overall.
