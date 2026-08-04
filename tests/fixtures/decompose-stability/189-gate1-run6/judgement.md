# Run 6 — judgement

*Content-vs-shape classification added (human decision). 25 obligations, 4 open
questions. See `prediction.md`, written before the run.*

## Verdict at the time

**Accurate breakdown.** One task-file fix made for a vague quantifier; see run 7.

> ## CORRECTION, written after run 7
>
> **The breakdown was not accurate, and I passed it.** Run 6 emitted **no
> obligation at all** for this scope exclusion:
>
> > *Interpreting the figures it produces, setting a threshold a rating must meet,
> > or reducing the variance it finds.*
>
> Run 5 covered it with one obligation (`report-only-no-acceptance-decision`);
> run 7 covers it with three. Run 6 has none — verified by grep across all three
> outputs. An entire scope exclusion vanished and I called the breakdown accurate.
>
> **This is a content difference, the serious class**, and it is the second time
> in this corpus that a requirement was silently dropped (run 4 lost half of a
> compound bullet). It is also the second time I have mis-scored a run: run 4's
> judgement read a dropped question as resolution, and this one read a dropped
> requirement as accuracy.
>
> **Why I missed it:** I audited the breakdown for *invented* obligations and for
> the requirements I was expecting, and a missing item in a section I was not
> looking at does not announce itself. Checking that every task-file section is
> represented is a different act from reading the obligation list and finding it
> reasonable — the first catches this, the second does not.
>
> The lesson generalises past me: **absence is the hard thing to see, which is
> exactly why the tool must report it rather than leaving it to a reader.** This
> is the argument for #189's content-difference figure being the primary output,
> not a secondary one.

## Scoring the pre-registered predictions

| # | prediction | outcome |
|---|---|---|
| 1 | ~28 obligations | **wrong** — 25 |
| 2 | the two definition bullets risk being promoted to obligations | **materialised in form, wrong in consequence** |
| 3 | no prediction offered on `report-format` | present |
| 4 | the rationale paragraph should produce no obligations | **correct** — none did |

**Prediction 1, why it undershot — and it is the interesting part.** The count came
in below the estimate because obligations that were *separate* in run 5 are
*bundled* in run 6, from unchanged text:

| run 5 | run 6 |
|---|---|
| `caller-supplies-input-models-runs-perturbation` + `defaults-for-input-models-runs-perturbation` | `caller-supplies-configurable-input-models-runs-perturbation` (one) |
| `single-default-model` + `small-default-run-count` | `default-single-model-small-run-count` (one) |

**This is the canonical `shape difference`** the human's distinction names, observed
in the corpus the same day the distinction was drawn. No requirement was lost; the
same content is partitioned differently. It is exactly what a determinism layer
should pin, and exactly what must *not* be counted against decomposition quality.

Note it runs in the opposite direction from run 3 → 4, where one sentence became
three obligations. Shape variance is bidirectional, so a metric that only counts
splits will miss half of it.

**Prediction 2 was right that the definitions would be promoted and wrong that it
would matter.** `define-content-difference` and `define-shape-difference` were
emitted as obligations. I predicted downstream stages could not evidence a
definition. On inspection that is wrong: they are phrased as *"Treat a content
difference as …"*, which is a testable requirement on the classifier's semantics —
a test can assert that a difference of that kind is classified as content. No
action. Recording the mis-prediction because the reasoning error (definition
therefore un-evidenceable) is the kind that would otherwise be repeated.

## `report-format` — the oscillation continues, with a pattern worth noting

| run | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| present? | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |

Present twice, absent twice, present twice. **Do not read this as a period-2
cycle.** Six runs over six different task files cannot establish a period, and the
pattern is exactly the kind of shape the eye invents in small samples. It is
recorded because if #189's resample axis reproduces runs-of-two on an *unchanged*
file, that would point at something structural rather than at sampling — and that
hypothesis is only checkable if the observation was written down before the
measurement existed.

## Open-question triage

| question | case | disposition |
|---|---|---|
| `small-run-count-value` — what number counts as "small"? | **fair** | Fixed the task file. Same vague-quantifier fault as run 2's "cheap enough to run without first deciding a budget" — I repeated the mistake in a new place. Made concrete. |
| `default-perturbation` — what should the default perturbation be? | implementation detail | No action. Genuinely mine to design; the task file says only that a default exists. |
| `perturbation-definition` — what perturbations, how represented? | implementation detail | No action. Fifth appearance. |
| `report-format` — what format, written where? | implementation detail | No action. Sixth appearance. |

Two of the four are new (`default-perturbation`, `small-run-count-value`), both
traceable to text the edit introduced. That is the decomposer working correctly.
