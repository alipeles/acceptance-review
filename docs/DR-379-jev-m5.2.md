# DR-379: Jev for "would this test fail under this defect" (M5.2)

- **Issue:** #379, part 1 of #371 (whether TypeSafe's Jev can take over the
  checker's fixed-label judgements)
- **Date:** 2026-10-13
- **Verdict:** not adopted as #371 framed it. Jev does not take over from the
  shipped judge; the shipped judge itself should be replaced. Whether Jev
  screens cases in front of its replacement: not enough evidence.
- **Evidence:** `docs/experiments/jev/FINDINGS-m5.2.md`, held-out figures in
  `docs/experiments/jev/m52/heldout.json`

## Against #371's adoption bar

#371's bar asks whether C, Jev first with the current model deciding the
unsure cases, stays within two points of that model, decides at least half the
cases itself, is at least as precise on a false "this test catches the defect",
and beats Mini's token probabilities (D) on cost, share decided or calibration.

**With the shipped judge (GPT-5.4 Mini, batched) as the current model,** the bar
is met trivially and says nothing. That judge was right 66.3% of the time on the
92 held-out cases; Jev alone was right 80.4%. A screen in front of a judge that
Jev outperforms is not the useful question.

**With no-tools Opus 5.5 as the model being screened,** Jev then Opus narrowly
misses the bar on the held-out cases:

| bar item | needed | measured | met |
|---|---|---|---|
| accuracy within two points | ≥ 92.6% | 93.5% (Opus 94.6%) | yes |
| share Jev decides alone | ≥ 50% | 47.8% | no |
| precision on a false "fails" | ≥ 0.929 | 0.912 | no |
| beats D | — | D not scored on held-out; no threshold pair met the bar on tuning | not measured |
| reliability rises steadily | — | not measured on held-out | not measured |

Both misses are within the noise of 92 cases: the precision gap is one extra
false "fails" (5 against 4). So the verdict for this pairing is not enough
evidence, not reject.

D is dropped for this judgement: Mini's token probabilities are badly
overconfident (log loss 1.16 against Jev's 0.37 on tuning), and no threshold pair
met the bar on tuning.

## What follows

- The model choice for the shipped judge (`src/acceptance/defects/pair_mapping.py::_ask`)
  is queued in `docs/DEFERRED.md` as an open decision, dated 2026-10-13. It is
  not resolved here.
- If Jev is ever used for this judgement, the context it needs is the whole
  function holding the edit; more code than that did not help it.
- #371's later parts (duplicate obligations, weak-evidence patterns, small
  classifiers, mapping) should check first whether their current model is the
  weak link, as it was here, before measuring Jev against it.

## Changed from the plan

#379's Acceptance was amended on closing (2026-10-13, owner's decision). Dropped:
C and D on the held-out set, held-out calibration, the five-run repeat check, and
held-out time per case. Reason: the shipped judge proved the wrong baseline, so
those items would measure designs already known to lose.
