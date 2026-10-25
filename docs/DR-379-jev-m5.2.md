# DR-379: Jev for "would this test fail under this defect" (M5.2)

- **Issue:** #379, part 1 of #371 (whether TypeSafe's Jev can take over the
  checker's fixed-label judgements)
- **Date:** 2026-10-13
- **Verdict:** adopt, for now. Jev decides first; the cases Jev is unsure of go
  to GPT-5.4 Mini, asked one case at a time with the requirement text, the
  original code and the defect description. This replaces the shipped judge
  (`src/acceptance/defects/pair_mapping.py::_ask`, Mini asked up to 40 cases
  per call with only the test and the defect description).
- **Decided by:** the owner, 2026-10-13, choosing cost over the more accurate
  Jev-then-Opus design.
- **Evidence:** `docs/experiments/jev/FINDINGS-m5.2.md`;
  `docs/experiments/jev/m52/heldout.json` and `jev-mini.json`

## The rule

Jev is given the targeted context (`m52/targeted_prompt.py`): the function
holding the edit with the edited line marked, the test with its imports and
helpers, and the project code the test calls. Its probability that the test
fails decides alone at 0.34 or more ("fails") and at 0.24 or less
("survives"). Cases in between go to Mini, whose "yes" probability decides at
0.5; if Mini gives no usable answer, Jev's own probability decides at 0.5.

Both cut-offs were fitted on the 137 tuning cases only, as the pair with the
highest tuning accuracy. They are close together and probably overfit: tuning
accuracy was 91.2%, held-out 85.9%. Re-fit them when more labelled cases
exist.

## Held-out results (92 cases)

| design | accuracy (95% range) | precision on a false "fails" | cost per judgement |
|---|---|---|---|
| shipped judge | 66.3% (56–75) | 0.789 | $0.0007 |
| Mini alone, one call per case (#371's approach D, without a threshold) | 82.6% (74–89) | 0.785 | $0.0006 |
| **Jev then Mini (adopted)** | **85.9% (77–92)** | **0.845** | **$0.0001** |
| Jev then Opus (rejected on cost) | 93.5% (87–97) | 0.912 | $0.027 |

Jev decides 96.7% of cases on its own.

## Against #371's adoption bar

- Accuracy within two points of the current judge: met; 19.6 points above it.
- Jev decides at least half the cases: met, 96.7%.
- At least as precise on a false "this test fails": met, 0.845 against 0.789.
- Beats Mini's token probabilities (D) on cost, share decided or calibration
  without losing accuracy: met on cost and accuracy against Mini alone. D's
  threshold rule was not scored on the held-out set; on tuning no threshold pair
  for D met the bar.
- Reliability rising steadily: not measured on the held-out set.

## Caveats

- The held-out set had already been scored once (for Jev then Opus) before
  Jev then Mini was tried. The rule was still fitted on tuning cases only.
- 92 cases; the ranges for Jev then Mini, Mini alone and Jev alone at a
  tuned cut-off (83.7%) overlap.
- Calibration and repeat consistency were not measured (dropped when #379's
  Acceptance was amended).
- Every judgement sends the test and nearby code to TypeSafe as well as OpenAI.
  That was accepted for this build on #379.

## Rejected

- **Jev then Opus:** 93.5%, but about 45 times the shipped judge's cost per
  judgement ($0.027 against $0.0006). The best option if accuracy matters more
  than cost later.
- **Mini alone, one call per case:** nearly as accurate (82.6%) at the
  shipped judge's cost and with no new vendor, but less precise on a false
  "fails" (0.785) and three points lower.
- **Keeping the shipped judge:** 66.3%.

## What follows

Wiring Jev into the pipeline is a separate issue, as #371 requires. It
includes adding Jev as a provider in `llm.py` with record and replay, and
pricing a real review. If Jev is used, findings it decides keep the static
evidence tier and must record that they carry no reasoning.

## Amended 2026-10-24

The fallback is Claude Sonnet 5.5, not GPT-5.4 Mini, by the owner's decision
after #412 moved model calls off OpenAI. Sonnet gives a yes/no answer rather
than a probability, so the 0.5 cut-off on Mini's "yes" probability no longer
applies; with no usable answer, Jev's probability still decides at 0.5. Jev's
own cut-offs (0.34 and 0.24) are unchanged. The held-out figures above were
measured with Mini and are not re-measured here; #385's benchmark acceptance
item is the check.

## Amended 2026-10-25

When Jev is unsure and the model gives no usable yes or no, the pair is now
recorded as unanswered, which a rating counts as unknown, instead of letting
Jev's probability decide at 0.5. In the band where the model is asked
(between 0.24 and 0.34) the 0.5 rule always read "survives", so an
obligation could be rated unsupported on a judgement nobody obtained, against
the rule that uncertainty is reported as uncertainty. Owner's decision, during
#385, which wires Jev into the pipeline.
