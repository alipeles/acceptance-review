# Judgement — #167 Gate 2, run 3 (`95b880a`)

Verdict: **INCOMPLETE**. 3 of 12 obligations below `strongly supported` — a
**third** distinct set. The diff since run 2 touched only `tests/test_cli.py`.

> **This file was rewritten.** My first judgement recorded all three findings as
> tool defects — "movement with no change in evidence". That was **wrong**. On
> examination every one was a real gap, including a silent file deletion I had
> introduced. The original reasoning is kept at the bottom because the error is
> the most instructive thing in this corpus.

| obligation | run 1 → 2 → 3 | verified judgement |
|---|---|---|
| `remove-stale-next-instruction-file` | STRONG → STRONG → `partial` | **REAL, and the most serious finding in the corpus.** `--json` mode deleted `.acceptance/next-instruction.md` and printed nothing: the removal notice sat on the text branch only. A silent deletion in the user's repo — precisely what the migration decision said must not happen. Every test covered text mode. Fixed in `52c52b8` (notice moved to stderr, so it appears in both modes). |
| `no-speculative-writing` | STRONG → STRONG → `partial` | **REAL.** No test snapshotted the repo around `recommendation` itself; `test_neither_the_pipeline_nor_the_cli_writes_into_the_reviewed_repo` covers `check` only. `test_retrieval_makes_no_model_call` proves no model call, which is a strictly weaker claim than no write — and "nothing is written speculatively" is the premise of the whole pull model. Fixed in `52c52b8`. |
| `spec-no-longer-describes-written-file` | STRONG → `partial` → `partial` | **REAL.** The spec still read "the recommendation may surface in the CLI, **a Markdown file**, …" (line 259). My test asserted only that the string `next-instruction.md` was absent — it was, so the test passed while the file-writing framing survived. Fixed in `52c52b8`. |

## Why the original judgement was wrong

The reasoning was: *the diff was additive, added tests cannot weaken evidence,
therefore a rating that fell did so for reasons outside the diff.* The first two
steps are sound; **the conclusion does not follow.** A rating that falls on an
additive diff can equally mean the judge has *finally noticed a hole that was
there all along*. That is what happened in all three cases — and in run 2's
`default-to-most-recent-review`, which I got right for the same reason I got
these wrong.

The corpus-wide pattern only became visible after this correction: **in 7 of the
8 unstable obligations the LOW rating was the correct one.** The instability is
not symmetric noise. It is biased toward the permissive direction, and the
`strongly supported` ratings are the unreliable ones. A tool that is wrong in
the direction of "looks fine" is far more dangerous than one that is merely
noisy, and it is the opposite of what a first reading of the churn suggests.

The one case I still believe was noise is `byte-identical-retrievals`
(STRONG → partial → STRONG), whose test invokes twice and compares bytes exactly
as the recommendation asked. Given the record above, treat even that as unsettled.

## Original judgement, kept for the record

> **No disposition taken.** Each of these is a rating that moved without a
> corresponding change in evidence. Filed rather than chased: continuing to add
> tests in response would be fitting to noise, and would let a run "pass" by
> coincidence rather than because the evidence improved.

The instinct not to chase noise was reasonable. Applied here it suppressed three
real findings, one of them a silent deletion of a file in the user's repo.
