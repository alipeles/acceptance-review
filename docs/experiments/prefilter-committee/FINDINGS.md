# Prefilter committee — findings

**In the deployment position (thresholds tuned on the other corpus), the
committee dominates the embedding union in both directions: it excludes 26.0%
and 30.6% of pairs while losing 1 of 127 and 2 of 268 recorded kills, where
the union without coverage manages either far less exclusion (9.7%) or far
more loss (10 kills at 39.1%).** Tuned on the corpus being scored, zero-loss
exclusion stays modest (21.4% to 27.3%) and the zero-loss property itself does
not survive transfer, so a shipped committee should be described as ~99%
recall against the judge at roughly a quarter of pairs excluded, never as
lossless.

## The matrix

Exclusion / kills lost. "Tuned on self" solves thresholds to zero loss on the
corpus shown; "transferred" applies the other corpus's thresholds verbatim.

| filter | #314 (127 kills) | #316 (268 kills) |
|---|---|---|
| embedding union, tuned on self | **22.0% / 0** | 9.6% / 0 |
| committee, tuned on self | 21.4% / 0 | **27.3% / 0** |
| embedding union, transferred | 9.7% / 1 | 39.1% / 10 |
| committee, transferred | **26.0% / 1** | **30.6% / 2** |
| coverage voter alone (binary) | 70.4% / 37 | 61.3% / 43 |
| locality alone (binary) | 77% / 80 | (see json) |

## 1. Zero-loss thresholds do not transfer

#314's thresholds were solved against 127 kills; applied to #316 the plain
union drops 10 of 268. The reverse direction drops 1 of 127. The zero-loss
figure is an in-sample statistic. Any adoption argument built on "keeps every
kill" is building on the corpus it was tuned on.

## 2. What coverage buys is robustness in transfer, not tuned-on-self exclusion

Tuned on self, coverage moved the number 0.6 points *down* on #314 and 17.7
points *up* on #316 — noise-to-large, corpus-dependent. Transferred, the
picture is consistent: coverage rescued 8 of the 10 kills the #314-tuned union
loses on #316, and turned #316's timid tuned thresholds (9.7% as transferred
union) into 26.0% on #314 at the same single lost kill. Aggressive thresholds
travel badly on their own; the coverage voter is what catches the kills they
drop in new territory.

## 3. The operating point, in dollars

At the transferred committee's ~26-31% exclusion, the #316 Gate 2 pair stage
($6.02: 3.87M prompt, 0.69M output, both scaling with pair count) sheds
roughly **$1.70 a run**, comparable to the prompt-caching ceiling and
cumulative with it. The residual 69-74% of pairs still gets judged, so this is
a discount, not a change of kind.

## 4. The same pairs bind everything, again

The three kills the transferred committees lose:

- `test_determinism.py::test_replay_reproduces_a_recorded_run_with_no_live_call`
  vs `conclusion-derived-from-recorded-judgements/derived-support-misses-unjudged-defects`
- `test_rating_regression.py::test_the_readme_states_what_is_and_is_not_read`
  vs `docs-update/benchmark-warning-docs-miss-new-boundary`
- `test_carry_forward.py::test_the_decompose_command_writes_a_ledger_entry_and_a_second_run_carries`
  vs `no-derive-rating-completion-or-recommendations-from-judged-pairs/pair-verdicts-added-to-review-state`

End-to-end replay, doc-text read, ledger carry: the exact families
`coverage-prefilter/FINDINGS.md` isolates as either coverage blind spots or
candidate judge error, and the same families that hold coverage's own 61-70%
exclusion hostage (37 and 43 lost kills, heavily concentrated there). Every
static filter measured across these two experiments hits the same wall. M8.4
injection on those pairs decides, both ways at once, whether the committee's
honest ceiling is ~28% or whether coverage's ~65% becomes available because
the binding kills were never real.

## 5. What this settles for adoption

A prefilter committee is worth shipping only as an explicitly non-lossless
cost gate: thresholds calibrated on accumulated corpora, every exclusion
recorded with the voter that made it (DR-164), recall against the judge
disclosed per corpus, and the reachability soundness rule untouched. It buys
about as much as caching. The decision it cannot substitute for is M8.4, which
is both the bigger cost lever and the only adjudicator for the pairs that cap
every static filter here.
