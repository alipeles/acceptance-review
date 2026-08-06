# Judgement — #202 Gate 1, run 3

Same `current-task.md`, byte-identical across all three runs. Run after two
changes the human asked for:

1. **The CLI renders the mapping requirement-major**, listing every requirement
   with the obligations mapped to it, and naming the other requirements each
   obligation also serves.
2. **The prompt tells the model what to do with a reference it cannot resolve.**
   The human's read of run 2 was that the model punted on the scope exclusions
   because it had no idea what `#204` referred to. That read was correct.

## Head-to-head

| | run 1 (flat) | run 2 (mapping) | run 3 (+ reference rule) |
|---|---|---|---|
| requirements identified | — | 44 | 44 |
| **yielding an obligation** | 30 of 42 | 35 of 44 | **43 of 44** |
| yielding nothing | 12, invisible | 9, with reasons | **1, correctly** |
| `undisposed` | n/a | 0 | 0 |
| scope exclusions yielding | **0 of 10** | 2 of 10 | **10 of 10** |
| obligations serving >1 requirement | not representable | 10 | 8 |

The single decline is `completion-01: Implementation`, disposed as *"Section
marker only; it introduces no checkable requirement."* That is correct — it is
the section marker, and it is the one requirement in the file that genuinely
imposes nothing.

## Finding 1 — the reference rule was the cause, and it is fixed

Run 2 declined eight scope exclusions with variants of *"a scope note pointing to
#204 rather than a standalone requirement."* Run 3 yields an obligation for all
ten. The added instruction — that an unresolvable identifier is a fact about the
model's inputs and not about the mandate, and that the clause *"which is #205"*
is an attribution rather than the content — moved 8 of 10 requirements.

This settles what run 2 left open. DR-202's *"Scope exclusions may be losing to
the prompt's own rule"* hypothesis is now **largely refuted as the primary
cause**: the positive-invariant instruction was already in place for run 2 and
recovered only 2 of 10. The unresolvable-reference confusion recovered the other
8. The prohibition framing was a contributing factor at most.

> **CORRECTED after Gate 2 run 2. The claim that this "fixed" the declines does
> not survive.** With the prompt unchanged and the task file edited by six added
> bullets and two rewordings, exclusions fell back to **1 of 10** yielding —
> including two that name no issue number at all, so the unresolvable-reference
> mechanism is not what is operating. The rule moved the outcome on one input; it
> did not make the behaviour stable. What stands is the refutation of the
> positive-invariant hypothesis, which rests on runs 2 and 3 together. What does
> not stand is any claim to a fix. Recorded on #193; see
> `dogfood-logs/202-gate2-run2/judgement.md` Finding 2.

This is worth carrying into #205 and #206, which own the prompt work: the
decomposer's failure was not that it could not phrase a prohibition, but that it
treated its own missing context as the mandate's deficiency.

## Finding 2 — the recall gain is partly bought with false links

**Do not read "43 of 44" as 43 correct.** Three of the ten scope exclusions were
attached to an obligation that is not their content:

| exclusion | what it says | mapped to | verdict |
|---|---|---|---|
| `exclusion-08` | do not align requirement ids **across two versions** of a task file (#209) | `obligation-requirement-ids-stable-across-byte-identical-runs` | **wrong** — that is `completion-07`'s content, and within-version stability is a different property from cross-version alignment |
| `exclusion-10` | do not **measure** whether decomposition recall improves | `obligation-decomposition-accuracy-marked-non-comparable` | **wrong** — that is `completion-14`'s content; not measuring a thing is not the same as annotating a figure |
| `exclusion-09` | do not **rebuild** #195's regression suite | `obligation-regression-suite-195-runs-unchanged` | **defensible** — "runs unchanged" does roughly entail "was not rebuilt" |

Both wrong links are to an obligation that already existed for a *different*
requirement, and in both cases the correct answer was a new obligation stating
the thing not to do.

**This is the predictable cost of forcing a disposition per requirement**, and it
is the first time this repository has observed it. Under the old flat shape these
three requirements produced nothing and the failure was invisible. Under the new
shape the model is obliged to say something, and for a requirement with no
natural obligation the cheapest compliant answer is to point at the nearest
existing one. The defect has moved from **recall to precision**, which is
progress — a false link is arguable and a silence is not — but it is not the
same as being fixed.

**Consequence for the metric:** the coverage count this run reports as
*"yielding obligations: 43"* is not a quality figure and must not be read as one.
A precision measure over the links belongs alongside it. That is an input to the
superseding issue DR-202 sequences for rebuilding #195's suite, and it should be
recorded there before that suite is built — otherwise the suite will score
coverage and call it accuracy.

## Finding 3 — two content defects persist unchanged from run 2

Neither was addressed by either change, and both reproduce exactly:

**A.** `obligation-flat-obligations-and-open-questions` — *"`decompose` returns
two flat lists: one of obligations and one of open questions."* — derived from
`task`, which is the paragraph describing **the defect being removed**. The same
paragraph also yields `obligation-no-missing-requirements-in-response`, the fix.
The breakdown therefore contains an obligation to preserve the flat list and an
obligation to replace it, and nothing flags the contradiction.

Three consecutive runs produce it. It is stable, not noise.

**B. — WITHDRAWN. This finding was wrong; the corrected reading is ground truth.**

> *Original reading, preserved:* `exclusion-04` — *"Requiring an open question to
> cite where the task file fails to answer it, which is #206"* — becomes *"An open
> question does not need to cite where the task file fails to answer it."*
> Out-of-scope inverted into must-be-false. A later stage could report this change
> as having failed to deliver an absence.

**Corrected reading.** There is nothing wrong with it. Set against the exclusions
this same run handled correctly:

| requirement | obligation |
|---|---|
| `exclusion-02` | Obligation derivation **is not partitioned** by requirement batch. |
| `exclusion-05` | Open-question resolution **does not read** the base revision. |
| `exclusion-07` | Semantically duplicate obligations **are not** de-duplicated. |
| `exclusion-04` | An open question **does not need to** cite where the task file fails to answer it. |

Same form as its siblings — *X is not done* — and if anything the mildest of the
four. The claimed inversion requires *"an open question must **not** cite …"*.
**"Does not need to" is a permission, not a prohibition**, so no diff can fail
this obligation by adding citations, which is precisely what the original finding
asserted would happen.

The error was mine, not the tool's: a bad inference over a reading I had already
got right. Run 2's version of this finding contains the correct gloss
(*"citations must not be **required**"*) and then draws the wrong conclusion from
it in the next clause. It was then carried into this run's judgement unchecked —
a judgement reused rather than re-derived, which is DR-180's lesson wearing the
other face: the stability of my own claim across three runs was not evidence for
it.

Nothing survives of this finding for run 3. (Run 2's *secondary* observation does
survive **for run 2 only**: the same obligation was typed `human_review` there and
`functional` here, which is #196's shape and a type-instability datum. It is not
a defect in the text, and it does not rescue the withdrawn claim.)

**Consequence:** the exclusion defects in this run are **three bad links out of
ten, not four**, and all three are one defect with one predictive signal.

## Finding 4 — the renderer

The output is now organised by requirement, which is the question a reader
actually has at Gate 1 (*did my mandate survive?*) rather than the question the
old layout answered (*what did the tool produce?*). Shared obligations are
annotated, so `obligation-many-to-many-requirement-obligation-linking` appearing
under `constraint-05`, `constraint-07` and `completion-06` reads as one
obligation with three links rather than three duplicates — the distinction
DR-202 decision 2 turns on.

Two smaller things fixed on the way: a wrapped bullet's list marker and internal
line breaks are flattened for display (`exclusion-06` rendered with a literal
`- ` and a mid-sentence break in run 2), and obligations that no requirement
claims now render under their own heading rather than vanishing — an unmapped
obligation is an invention or a mapping failure, and both are findings.

## Disposition

| finding | disposition |
|---|---|
| 1 — reference rule fixed the declines | delivered; refutes DR-202's prompt-rule hypothesis as primary cause. Carry to #205/#206 |
| 2 — three false links, two clearly wrong | **new defect, unfiled.** Recall converted to precision. Needs a link-precision measure before #195's suite is rebuilt |
| 2 — three false links | filed as **#210** (child of #181), blocked on **#211** |
| 3A — problem statement became an obligation | **unfiled**, stable across three runs, #181 family |
| 3B — scope exclusion inverted | **withdrawn — the finding was wrong, not the tool** |
| 4 — renderer | delivered |

The link-precision measure Finding 2 calls for is **#211**, which supersedes #195
and blocks #210: nothing about the linking behaviour should be changed before a
number exists that can tell whether the change helped.

`current-task.md` is unedited across all three runs, so the comparison is clean.

## What this run does not establish

One run, one task file, one repository, and the task file's author is the change's
author. The 35 → 43 movement is a single sample and is not a rate (DR-180; run 7
of the decompose-stability corpus). What it does establish is causal and
categorical: the same task file, with one prompt paragraph added, moved eight
specific requirements from declined to yielded, and the reason those eight were
declined was stated in the model's own dispositions in run 2.
