# Task
Make the §11.1 accuracy metrics match reviewer criteria to ground truth semantically, so a correct-but-differently-worded criterion counts as matched instead of scoring zero under exact-string matching.

## Constraints
- The obligation-keyed joins (gap detection, decomposition accuracy, mapping accuracy) currently match reviewer output to ground truth by exact description string; a real model decomposition never matches verbatim, so it scores near zero.
- Align semantically-equivalent criteria via a schema-constrained model judgment, recorded for replay, bijective so an over-decomposed extra criterion stays unmatched and costs precision.
- Remap reviewer-side descriptions through the alignment before the existing set intersection.
- Preserve backward compatibility: with no client, the alignment is empty (identity remap, exact-string match), so existing hand-aligned fixtures score unchanged.

## Completion expectations
- Implementation
- Unit tests: a reworded reviewer criterion scores zero under exact match and matched under semantic alignment; the alignment is bijective; empty sides make no model call. A live run shows decomposition_accuracy on real decompose output is meaningful, not near zero.
