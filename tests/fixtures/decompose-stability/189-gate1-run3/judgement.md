# Run 3 — judgement

*After making the defaults concrete. 20 obligations (from 18), 0 open questions
(from 3).*

## Verdict at the time

**Gate 1 passed.** 20 obligations, all `explicit`, no `human_review` type, no open
questions. All eight of #189's acceptance items represented, nothing invented.

**And the pass is partly unexplained.** Both things are true and the second does
not cancel the first.

## The finding — two open questions vanished without being addressed

The run 2 → run 3 edit is a single bullet replacement, reproduced in full in
`task-diffs.txt`. It states the defaults. It is relevant to exactly one of the
three outstanding questions:

| question | touched by the edit? | run 3 |
|---|---|---|
| `oq-default-values` | **yes** — the edit states the defaults | gone, **earned** |
| `oq-perturbation-definition` | no | **gone, unexplained** |
| `oq-output-format` | no | **gone, unexplained** |

Neither of the two survives in any form. The task file says no more about output
format or about how a perturbation is specified than it did in run 2.

**This is the corpus's load-bearing observation.** An open question is a
first-class output of this tool — "uncertainty is first-class" is a standing
invariant, and #113 already tracks open questions being silently dropped
*downstream*. This is a different and earlier failure: they are dropped at the
point of production, in response to an unrelated edit.

It is the same shape as the defect #180 documents for evidence ratings — a
judgement moving because something irrelevant to it changed — but in the
decompose stage. That is the direct argument for putting decompose inside #189's
measured surface rather than watching only the evidence stages.

## Second finding — obligation count rose on an edit that added one bullet

18 → 20. The new pair is:

- `single-default-model-and-small-run-count` — *"Make the default model set a
  single model and the default run count a small number."*
- `opt-in-multi-model-cost` — *"Make measuring more than one model an explicit
  caller choice rather than the default cost of a run."*

These are one requirement stated in the two clauses of a single sentence, split
into two obligations. #144 again, at finer grain than run 1's cross-section
duplicates — and evidence that #144's dedup pass has to work *within* a sentence,
not only across sections. Left in place: the task file wording is defensible, and
fixing it by flattening the sentence would be shaping the input to flatter the
tool.

## What is *not* instability

Stated so nobody re-derives it. Two changes across these runs were correct
responses to a genuinely improved task file and must not be counted as variance:

- the 24 → 18 duplicate collapse (run 1 → 2);
- the loss of the `human_review` type (run 2 → 3), whose vague bullet was
  replaced with a checkable one.

Both were caused by the edit. Only the two dropped questions and the intra-sentence
split are unexplained.

## The trap

*"Run 3 is clean, so Gate 1 passed and the earlier runs were just a bad task
file."* Gate 1 did pass and the task file genuinely was bad — but the clean result
was reached partly by an unexplained drop of two open questions, and only the diff
distinguishes an earned clean run from a lucky one. Same structure as the
inference recorded in `docs/DR-180-evidence-judgement-instability.md`: check the
finding on its merits first, attribute to instability only after.

## Disposition

- Two dropped questions → recorded as evidence on #189 (comment), which is the
  issue that will quantify it. Not filed separately: one observation is not a
  rate, and #189 exists to produce the rate.
- Intra-sentence duplicate pair → recorded against #144.
- Gate 1 → passed, at `0a0fb78`, with the caveat above stated to the human rather
  than absorbed.
