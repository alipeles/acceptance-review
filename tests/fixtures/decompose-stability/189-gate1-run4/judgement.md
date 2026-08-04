# Run 4 — judgement

*Decompose stage brought into the measured surface (human decision). 20
obligations, 0 open questions. See `prediction.md`, written before this run.*

## Verdict at the time

**Gate 1 does NOT pass on this run.** A requirement lost half its content. Fixed
the task file and re-ran; see run 5.

## Scoring the pre-registered predictions

| # | prediction | outcome |
|---|---|---|
| 1 | obligation count rises to ~22–23 | **wrong** — stayed at 20 |
| 2 | two specific new obligations appear | **half right** — both appear, but one is degraded (below) |
| 3 | 0 questions if run 3's zero was earned; `oq-output-format` returns if it was instability | **0 questions** — see reading below |
| 4 | risk of an obligation invented from the motivation paragraph | **did not occur** — `measure-whole-pipeline` traces to a real sentence I wrote |

**Prediction 1 was wrong in an informative way.** The count held at 20 not because
the decomposition was stable, but because it re-split elsewhere: run 3's single
`harness-runs-review-pipeline-repeatedly` became three obligations in run 4
(`harness-runs-review-pipeline-repeatedly`, `harness-supports-chosen-model-set`,
`harness-reports-judgement-movement`) from the same unchanged sentence. A stable
total concealing a re-split underneath is worse for a reader than a moving total,
because it looks like stability. **Any variance metric #189 produces must compare
aligned obligation sets, never counts.** This is the strongest design finding of
the Gate 1 series and it validates the `align_obligations` constraint.

**Prediction 3 is inconclusive, not a clean negative.** The request changed again
between runs 3 and 4, so this was never a controlled test of whether
`oq-output-format` returns. It weakens the run-3 finding somewhat — two
consecutive zero-question runs is more consistent with "the questions were
genuinely resolved" than with pure noise — but it cannot settle it. Only #189's
resample axis, N draws over one unchanged file, can. Recorded here so the
weakening is not overstated later.

## Finding 1 — a requirement lost half its content

Task file (mine, this run):

> *The harness reports how the decomposition itself varies across runs of one
> task file: which obligations appear in some runs but not others, **and which
> open questions do**.*

Obligation produced:

> `decomposition-instability-observed`: *The harness reports decomposition
> instability as an observed phenomenon across runs of one task file.*

The open-questions half is **gone**, and the obligations half is softened from a
specific reportable into "reports instability as an observed phenomenon".

This is the most serious finding in the corpus so far. A dropped requirement is
exactly the failure this product exists to detect in others, and it is invisible
downstream: no later stage can evidence a requirement that was never extracted.
It also happens to be the requirement that covers **open-question stability** —
the very defect run 3 exhibited.

**Disposition: fixed at source.** The bullet was compound (two reportables joined
by "and"), and compound obligations are a known weak point. Split into two
bullets. This is task-file authoring, not a tool excuse — but the tool's
susceptibility to compound phrasing is real and belongs to #144's family.

## Finding 2 — obligation text lost a symbol on byte-identical input

The constraint text is **byte-identical** between runs 3 and 4 (verified by
`grep`; the constraint sits in an unedited section):

> *The statistics come from the variance path the benchmark harness already has,
> `benchmark/scoring.py::disclose_variance`, rather than a second one written for
> this task.*

| run | obligation text |
|---|---|
| 3 | *Source statistics from the existing benchmark variance path in `benchmark/scoring.py::disclose_variance`.* |
| 4 | *The statistics come from the existing benchmark variance path.* |

The symbol is dropped in run 4. The same happened to the new alignment
constraint: `align_obligations` became "the existing alignment function".

**Why this matters beyond tidiness.** A standing invariant is that every finding
links to exact requirement text and exact code locations. An obligation that has
discarded the one identifier in its source text gives the mapping stage strictly
less to work with — and mapping precision is already a tracked defect (#173). This
is a **precision** loss on unchanged input, distinct from the membership churn the
rest of this corpus documents.

**Disposition: attributed to the tool, recorded against #181** (decomposition
umbrella). Not fixed at source — the task file already names the symbol in
backticks, which is as strong a signal as the input can carry. There is nothing
to rewrite.

## Accuracy of the rest

The other 18 obligations are accurate and traceable. Nothing invented —
prediction 4's risk did not materialise; `measure-whole-pipeline` traces to the
sentence *"The measured surface is the whole pipeline, not only the evidence
stages"*, which is a real requirement.

Splitting `default-model-set-single-model` and `default-run-count-small` into two
is a fair reading of a two-clause sentence, and better than run 3's handling of
the same text (which produced a requirement/rationale pair — see #144 comment).
