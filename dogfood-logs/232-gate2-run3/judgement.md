# Judgement — #232/#219/#230 bundle, Gate 2, run 3

Base `eb182de`, head at the `.acceptance/ignore` commit. Same verdict as run 2:
**INCOMPLETE**, the same 6 obligations below strongly supported, all 15
addressed, no open questions.

## What this run establishes

**The output-file collision is fixed, and this run is the proof.** Runs 1 and 2
had to be captured outside the repo and copied in, because
`check ... > dogfood-logs/<run>/output.log` put the log into the diff under
review and replay then failed with `no recorded transcript`. This run wrote its
log directly into the run directory, in both record and replay mode, and both
succeeded.

Fixed with `.acceptance/ignore` (#105) rather than new code — the mechanism
already existed. Only `.acceptance/cache/` and `.acceptance/reviews/` are
gitignored, so the file is committed and applies to every clone.

**The 6 findings reproduce exactly.** Same obligation set, same ratings as run 2.
So the run 1 -> run 2 movement was driven by the diff changing (two tests added),
not by run-to-run noise over an identical input. That narrows the #180 finding
usefully: the instability is *sensitivity to an unrelated part of the diff*, not
irreproducibility.

## Still open, and attributed rather than iterated on

The 6 below-strong ratings are #180 (judgement stability) plus #182 (mapping
churn), unchanged from run 2's judgement. `tests-no-live-model-calls` remains
partially supported with 8 mapped tests where it was strongly supported with 6.

Human's call, recorded: note these and do not let them hold the change up.

## Residual, not fixed

The error message on a missing transcript still attributes the miss to an edited
prompt and sends the reader to re-record the corpus. That was wrong here and
cost a diagnostic cycle. Left in the queue; it needs a call on where it belongs.
