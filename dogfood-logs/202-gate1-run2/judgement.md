# Judgement — #202 Gate 1, run 2 (post-implementation verification)

Same `current-task.md` as run 1, byte-identical. Run after implementing #202, at
the human's instruction, as a test of the change itself: the claim under test is
that the mapping makes lost content **visible**, not that it stops the loss.

Re-recorded, because the prompt changed and the request key hashes it.

## Head-to-head

| | run 1 (flat list) | run 2 (mapping) |
|---|---|---|
| requirements identified by the code | — | **44** |
| obligations produced | 25 | 23 |
| requirements yielding an obligation | 30 of 42 | **35 of 44** |
| requirements yielding nothing | **12, invisible** | **9, each stated with a reason** |
| requirements the response failed to account for (`undisposed`) | n/a | **0** |
| obligations serving more than one requirement | not representable | 10 |
| open questions | 1 | 0 |

## Finding 1 — the deliverable works, and this is the evidence

**Zero requirements came back `undisposed`.** Every one of the 44 was accounted
for. The nine that yielded nothing are each recorded as a `no_obligation`
disposition carrying a reason, and all nine are rendered.

Run 1's twelve losses were **silence**. Run 2's nine are **claims**. That is the
whole of DR-202 decision 3 — *forcing an answer per requirement makes silence
unrepresentable; a wrong disposition remains wrong, but it is a claim a human can
reject at Gate 1 and a benchmark case can score.* The mechanism did what the DR
said it would do.

## Finding 2 — and I reject some of those claims, which is the point

Eight of the nine declines are scope exclusions, each dismissed with a variant of

> *This is a scope note pointing to #204 rather than a standalone requirement.*

**I disagree.** A scope exclusion is a requirement: the delivered change must not
do that thing, and whether it did is checkable against the diff. The reading that
a bullet naming a sibling issue "adds no requirement of its own" is defensible for
`exclusion-09` and `exclusion-10`, and wrong for the six that name #204/#205/#207/
#208/#144/#209 — those are exactly the constraints keeping this change
representational.

Recording the disagreement rather than acting on it: the disposition is a
judgement the model is entitled to make and I am entitled to overrule, and the
mechanism for overruling it is the human at Gate 1. Under run 1's shape I could
not have had this argument at all — the same eight bullets simply were not
mentioned.

**This is the residual of Finding 1 in run 1's judgement**, and it survives into
a form that is now tracked rather than invisible. The prompt now states
explicitly that a scope exclusion is a requirement and yields an obligation; two
of ten took it (`exclusion-01`, `exclusion-04`) where none did before, and eight
did not. DR-202's *"Scope exclusions may be losing to the prompt's own rule"*
hypothesis is **partially supported and not settled**: the positive-invariant
conflict was not the whole cause, since instructing against it recovered only two
of ten. Recorded against #205, which owns the typing and prompt pass.

## Finding 3 — the never-duplicate property is recovered

Run 1 lost it in both its statements. Run 2 maps it:

> `obligation-many-to-many-requirement-obligation-link`
> <- constraint-05, constraint-06, **constraint-07**, completion-05, completion-06

`constraint-07` is *"An obligation is never duplicated so that each requirement
can hold its own copy."* It is now visibly served rather than silently dropped,
and the obligation serving it also serves its positive restatement under
Completion expectations — which is itself the many-to-many case DR-202 decision 2
exists for, arriving unprompted. Run 1's Finding 2 is resolved.

Ten of 23 obligations serve more than one requirement. Under the old shape every
one of those was either a duplicate or a silent loss.

## Finding 4 — two obligations are wrong, and neither is a mapping defect

**A.** `obligation-flat-obligations-and-open-questions` — *"`decompose` returns
two flat outputs: a flat list of obligations and a flat list of open
questions."* — derived from `task`.

That is the **problem statement**, restated as a property to preserve. The same
paragraph also produced `obligation-cover-all-requirements`, which is the fix. So
the breakdown contains an obligation to keep the defect and an obligation to
remove it, from one paragraph, and nothing flags the contradiction.

Partly my wording: the Task section opens by describing the current behaviour
before saying what to change. But the section ends *"Make decomposition return a
mapping"*, and a decomposer that reads a problem statement as a requirement to
preserve the problem has misread the mandate, not the sentence. Recorded against
**#181**; filing deferred pending the human's read, since it may belong under
#205 with the typing work.

**B.** `obligation-open-question-no-citation-required` — *"An open question does
not need to cite where the task file fails to answer it."*, typed `human_review`,
derived from `exclusion-04`.

The exclusion says citations are **#206's** job, not this change's. The
obligation inverts that into an assertion that citations must **not** be
required — turning "out of scope" into "must be false". A later stage could
report this change as failing to deliver an absence. The `human_review` type on
a statically-checkable statement is separately #196's shape.

Both are content defects in a change that only claimed to be representational —
so they are **not** regressions introduced by it, but they are not fixed by it
either, and neither would have been visible before.

## Finding 5 — the open question disappeared

Run 1 raised `requirement-id-format-ambiguity`; run 2 raises nothing, on
byte-identical input. That is #193's oscillation defect in its exact documented
form.

**It is not evidence here.** The prompt changed substantially between the runs,
so the two are not samples from one distribution — DR-180's discipline applies
and one pair of runs licenses no conclusion. Recorded so a later reader does not
mistake it for either a fix or a regression. The question itself was triaged
case 2 in run 1 and was already answered.

## Finding 6 — cosmetic: a wrapped bullet keeps its markdown

`exclusion-06`'s registry text renders as

> `- Deciding whether the decomposer receives base-revision code context, which is\n  #208.`

with its list marker and line break intact. This is the pre-existing `_span`
fallback in `task_file.py` — a bullet wrapped across lines has no literal match,
so the whole block is used, and the span invariant `source[start:end] ==
span.text` requires keeping it verbatim. Harmless to the mapping, mildly ugly in
the prompt and the report. Not fixed here: touching `_span` risks the citation
invariant for a presentation nit.

## Disposition

| finding | disposition |
|---|---|
| 1 — mapping works | none needed; it is the deliverable |
| 2 — eight exclusions declined | attributed to **#205**; recorded, human overrules the claim |
| 3 — never-duplicate recovered | resolves run 1's Finding 2 |
| 4A — problem statement became an obligation | new defect, **#181** family, filing deferred to the human |
| 4B — scope exclusion inverted into a prohibition | new defect, related to **#196**/#206, filing deferred |
| 5 — open question vanished | no conclusion drawn; #193 |
| 6 — wrapped-bullet text | not fixed, reason recorded |

**`current-task.md` was not edited between run 1 and run 2**, so the comparison is
clean.

## What this run does not establish

It is **one run on one task file, in one repository, by the author of both the
task file and the change**. Recall moved 71% → 80% on a single sample, which by
this repository's own findings (DR-180, run 7 of the decompose-stability corpus)
is not a rate and must not be quoted as one. What it does establish is
categorical rather than statistical: **`undisposed` was zero and nine declines
were rendered with reasons**, which is a property of the shape, not of the
sample.
