# #195 Gate 1, run 1 — judgement

*`decompose --mode record` at `dbb342f`. 29 obligations, 3 open questions.*

## Verdict

**Gate 1 does NOT pass.** Nine requirements produced no obligation, and all three
open questions are the "wrong question" case — answerable from the task file
alone. Stopped and reported to the human rather than proceeding or rewriting.

## Finding 1 — the both-directions requirement was dropped entirely

Four Completion expectations produced no obligation:

| task-file bullet | obligation |
|---|---|
| *A decomposer that drops content fails the suite.* | none |
| *A decomposer that raises every open question fails the suite.* | none |
| *A decomposer that splits every sentence into its own obligation fails the suite.* | none |
| *Every case carries assertions of the same kind as the other cases rather than passing trivially.* | none |

The first three are the single most load-bearing requirement in #195 — its
Acceptance names both a permanently lossy and a permanently permissive decomposer
as required failures, because a suite that only asserts one direction is passed by
"stop moving". They are three consecutive single-clause sentences in one section,
and all three vanished.

This is a **content difference** in the corpus's own taxonomy, and it is the
defect the suite being specified exists to catch — reproduced live on the task
file that specifies it.

**Disposition: attributed to the tool.** Recorded against #181 (decomposition
umbrella) / #193. Not fixed at source: the bullets are single-clause imperatives
and there is nothing to reword.

## Finding 2 — five of eight scope exclusions produced no obligation

| scope exclusion | obligation |
|---|---|
| Changing how any decomposition is produced | `preserve-existing-decomposition-stage` |
| Reducing the instability the corpus documents | `preserve-instability-documentation` (and `preserve-no-variance-reduction`, a duplicate) |
| Setting a threshold a variance or accuracy figure must meet | `preserve-no-thresholding` |
| Deciding which type `record-run-provenance` should carry | **none** — inverted into open question `clarify-record-run-provenance-type` |
| Measuring resample variance over one unchanged task file | **none** |
| Producing new corpus runs by re-running `decompose` | **none** |
| The rating-stability corpus and #190's suite over it | **none** |
| Modifying corpus files other than the README | **none** |

This is the run-6 defect of the corpus itself — a scope exclusion vanishing —
recurring, and it is why #153 exists. The fourth row is the sharpest: an exclusion
saying *do not decide X* did not merely disappear, it came back as a question
**asking me to decide X**.

**Disposition: attributed to the tool**, recorded against #153 and #181.

## Finding 3 — all three open questions are answerable from the task file

Per CLAUDE.md's Gate 1 triage, each falls in the third case: **stop and tell the
human**.

| question | where the task file answers it |
|---|---|
| `clarify-record-run-provenance-type` — invariant, docs_config or functional? | *"Which of the three types is correct is not established by the corpus"*, plus the Scope exclusion *"Deciding which of its three observed types `record-run-provenance` should carry"* |
| `clarify-run-4-reading` — dropped, or resolved? | the ground-truth table: *"run 4 \| the two open questions were dropped, not resolved; the original judgement leaned toward genuine resolution and run 5 falsified it"* |
| `clarify-run-6-reading` — not accurate, or the original wording? | the ground-truth table: *"run 6 \| the breakdown was not accurate; ... the correction written after run 7 stands above the original wording"* |

Runs 4 and 6 are answered in a dedicated, titled table whose stated purpose is to
settle exactly these two readings. This is **#178** — the decomposer anchoring on
one section and never reconciling a term against the section that defines it —
recurring for the sixth audited time, now on a table written specifically to
pre-empt it.

**Disposition: attributed to the tool**, recorded against #178.

## Finding 4 — one compound bullet lost its second half (task-authoring)

> *A case's input is the `current-task.md` of the corpus run that case derives
> from. **No task text is copied into the case.***

`preserve-real-run-inputs` covers the first sentence; nothing covers the
prohibition. Same shape as the corpus's run-4 truncation.

**Disposition: fix at source** on the next iteration — split into two bullets.
This one is mine. Writing a compound bullet in a task file whose subject is
compound-bullet content loss is the mistake being documented.

## Finding 5 — two prohibitions typed `human_review`

`preserve-no-thresholding` and `preserve-no-variance-reduction` are both
statically checkable prohibitions on the harness's behaviour, both typed
`human_review`. This is **#196** exactly, and it is the run-7 finding of the very
corpus this task is encoding — reproduced on a task file that lists that finding
as ground truth.

As typed they are a mandatory Gate 2 pause by construction.

**Disposition: attributed to the tool**, recorded against #196.

## Accuracy of what was produced

Nothing invented. The 29 obligations that exist are traceable and accurate, and
the five content-loss entries of the ground-truth table each produced their own
obligation (`report-lost-*`), which is the part that most needed to survive. The
failure is entirely one of absence.

Which is the corpus's own lesson, arriving on schedule: *absence is the hard thing
to see, which is exactly why the tool must report it rather than leaving it to a
reader.*
