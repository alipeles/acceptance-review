# Judgement — #202 Gate 1, run 1

Run at `4ec4470` (branch `202-requirement-obligation-mapping`, before any code).
`decompose --task current-task.md`, default model `openai/gpt-5.4-mini`.

**Gate 1 does not pass.** The breakdown is not one I would defend: 12 of 42
substantive requirements produced no obligation. Every loss is attributable to
the defect #202 exists to fix, and the finding is recorded against #202 — but the
CLAUDE.md instruction at Gate 1 step 2 is to stop rather than proceed past an
inaccurate breakdown, so this is escalated to the human rather than dispositioned
by me.

## What the run produced

| | count |
|---|---|
| requirement bullets in the task file | 43 (one is the `Implementation` marker) |
| substantive requirements | 42, plus the Task behavior paragraph |
| obligations produced | 25 |
| open questions raised | 1 |
| requirements producing no obligation | 12 |

Recall ≈ 0.71. Precision ≈ 1.0 — **nothing was invented**. Every obligation
produced is accurate and traceable to text that is actually in the file. The
failure is entirely absence, which is the shape DR-202 records (~0.75 / ~1.0).

## Finding 1 — every Scope exclusion produced nothing

All **10 of 10**. Not one of the section's bullets yielded an obligation:

| requirement |
|---|
| *Changing which obligations a task file decomposes into.* |
| *Partitioning obligation derivation by requirement batch, which is #204.* |
| *Assigning obligation types in a separate pass, which is #205.* |
| *Requiring an open question to cite where the task file fails to answer it, which is #206.* |
| *Reading the base revision during open-question resolution, which is #207.* |
| *Deciding whether the decomposer receives base-revision code context, which is #208.* |
| *De-duplicating semantically duplicate obligations, which is #144.* |
| *Aligning requirement ids across two versions of a task file, which is #209.* |
| *Rebuilding #195's regression suite to bind its labels to the mapping.* |
| *Measuring whether decomposition recall improves as a result of this change.* |

#195's Gate 1 lost 5 of 8. This run lost 10 of 10, on a file written by an author
who had just read DR-202 and knew the section was the weak one.

**This is evidence for DR-202's untested hypothesis**, recorded there under
*"Scope exclusions may be losing to the prompt's own rule"*: the system prompt in
`requirement/obligations.py` commands that every obligation be a positive
invariant and never a prohibition, and the Scope exclusions section is entirely
prohibitions. A total loss rather than a partial one is what a structural
conflict looks like, as against the attention-shedding that explains the
Completion-expectation losses. It is not proof — one run, and these ten bullets
are also unusually reference-shaped (*"which is #204"*) — but the hypothesis
predicted this section specifically and this is the strongest observation of it
so far.

Recorded against #202. Note that the fix #202 delivers makes the loss *visible*
(each of these ten becomes an undisposed requirement in the mapping) without
necessarily making it *stop* — the prompt-rule conflict, if that is the cause,
is a #205 / prompt concern.

## Finding 2 — the never-duplicate property was lost in both its statements

DR-202 decision 2 turns on it: *an obligation is never duplicated so that each
requirement can hold its own copy.* The task file states it twice, once as a
prohibition and once positively:

| section | text | obligation |
|---|---|---|
| Constraints | *An obligation is never duplicated so that each requirement can hold its own copy.* | none |
| Completion expectations | *That same case yields one obligation rather than two.* | none |

Both lost. The positive statement is the one that matters here: it defeats the
simple reading that prohibition-shaped text is the whole story, and it means the
loss is not fully explained by Finding 1's hypothesis.

`many-to-many-requirement-obligation-link` covers the relation and the
link-to-both half, so what survived is the permissive half of decision 2 and what
vanished is its constraint — the half that stops the obvious wrong
implementation.

## Finding 3 — three requirements survived only inside a broader obligation

Not losses, recorded because they degrade what a later stage can check:

| requirement | folded into | what was lost |
|---|---|---|
| *A requirement that yields no obligation appears in the mapping carrying its reason.* | `requirement-disposition-recorded` | the reason being present |
| *A requirement that yields no obligation is visible in the rendered report.* | `render-mapping-in-section-16-report` | that the **empty** case specifically must render — DR-202's *"not absent from it"* |
| *A requirement stated twice in different sections yields one obligation linked to both requirements.* | `many-to-many-requirement-obligation-link` | the concrete two-sections case |

Each generic obligation can be shown addressed by an implementation that fails
the specific one. This is the compound-clause weakness DR-202 lists under §Open,
in its milder form.

## Finding 4 — the shape differences are correct

Two Constraints pairs were each bundled into one obligation, from text that
states one thing across two bullets:

| constraints | obligation |
|---|---|
| *the relation is many-to-many* + *an obligation serving two requirements is linked to both* | `many-to-many-requirement-obligation-link` |
| *every requirement carries exactly one disposition* + *the dispositions are: …* | `requirement-disposition-recorded` |

Both are the same content partitioned differently, which
`tests/fixtures/decompose-stability/` establishes is **not a defect**. Recorded
so a later reader does not count them as losses. Under #202's own deliverable
these become one obligation linked to two requirements — the case decision 2
exists for, arriving unprompted.

## Open question triage

One question raised:

> `requirement-id-format-ambiguity`: What exact string format should requirement
> ids use for the section-and-ordinal scheme (for example, `§3.2`, `3-2`, or
> another canonical form)?

**Case 2 — implementation detail deliberately left to the coding agent. No
action.** The task file fixes the id *scheme* (section plus ordinal, parse order)
and its acceptance test (*identical across two runs over byte-identical text*),
which is format-independent. Which spelling realises the scheme is mine to pick,
and it is picked: `completion-07`, zero-padded to two digits, recorded on #202.

Applying the CLAUDE.md tie-break — *rewrite when the tool's response makes you
regret your wording* — I do not. Naming the exact string in the mandate would be
over-specifying an implementation choice, and the question is a correct
observation about a decision that is mine.

This is the one part of the run that is unambiguously right: the question is
fair, singular, and answerable by a human in one line. Contrast #195's Gate 1,
where all three questions raised were answerable from the task file itself
(#178's shape). No #178 recurrence here.

## Disposition

Every negative finding is **attributed to a tool defect**, and the backlog items
exist and predate the run:

| finding | tracked by |
|---|---|
| 1 — Scope exclusions produce nothing | #202; hypothesis recorded in DR-202 |
| 2 — never-duplicate property lost twice | #202 |
| 3 — specific requirements folded into generic ones | DR-202 §Open, *compound-clause splitting* |

No finding is attributed to weak wording in `current-task.md`, and the file is
**not rewritten**. Rewording the ten Scope exclusions into shapes the decomposer
handles better would work around the defect this task fixes and would destroy the
evidence in Finding 1. The file stays as written.

## Why this run matters beyond its own gate

It is the first Gate 1 run against a task file authored *after* DR-202, by an
author who knew where the recall goes and wrote single-clause bullets throughout
to avoid the known compound-clause loss. Recall still landed at 0.71. That the
countermeasure available to the task-file author does not move the number is the
argument that the fix has to be structural — which is DR-202's central claim,
and this is a second independent observation of it.
