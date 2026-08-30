# Prefilter the pair set — findings

**No candidate filter is worth adopting.** The best of them excludes 14.6% of
the 12,450 pairs without skipping a recorded kill, which is worth about 50 cents
on a $4.25 review, and that 14.6% is an upper bound measured on the same data
that chose its thresholds. Backing off far enough to leave any margin drops it
to single digits. The recommendation is to keep judging every pair and look
elsewhere for the cost.

Measured on #314's Gate 2 run: **12,450 pairs, 127 kills, a 1.0% kill rate**,
75 defects against 166 tests, base `5554c79` head `2945551`, run
`fc5fdcb24820a37e`. Method and traps are in `README.md`; raw numbers in
`findings.json`.

## What each candidate does

Every figure is the most the filter can exclude while keeping all 127 kills.

| filter | encoding | excludes | at |
|---|---|---|---|
| discovery signal touches the defect's file | none needed | **0%** | binary |
| defect description vs test source | query/document | 10.2% | 0.321 |
| defect description vs test source | neither | 12.3% | 0.532 |
| implicated code region vs test source | document/document | 10.6% | 0.475 |
| implicated code region vs test source | neither | 3.2% | 0.617 |
| all three together, rejecting only when all reject | query/document | **14.6%** | 0.369 / 0.512 |
| all three together, rejecting only when all reject | neither | 14.2% | 0.542 / 0.873 |

## 1. The free baseline fails outright, and fails the way the code predicted

Asking whether a test's discovery signal touches the defect's own file excludes
77% of pairs — and **skips 80 of the 127 kills**. It is binary, so there is no
threshold to soften: its only operating point loses 63% of the kills.

That is the exact case `defects/reachability.py`'s docstring sets out as the
reason one-hop name overlap cannot prove absence, now measured rather than
argued. The skipped kills are end-to-end tests —
`test_two_runs_over_the_same_input_agree_byte_for_byte` and its siblings — that
drive the pipeline without naming any changed symbol and would still fail on a
defect in `report.py` or `pair_mapping.py`. One hop cannot see the second edge.

Broken into its four signals, only *called names* carries anything: alone it
excludes 80.7% and keeps 42 kills. *Referenced names* keeps 5. *Imported
modules* and *name match* keep none.

**The "own file" signal is structurally inert, not accidentally zero.** The
enumerator runs over `non_test_changes`, so no defect's code refs can name a
test-category file, so a test's own file can never be one of the defect's files.
I verified this on the corpus: the 11 files named by defect code refs are all
`source` or `other`, and none of the 4 test-category files in the change set is
among them.

## 2. The embedding filters work, and do not work well enough

Both clear the free baseline easily — they lose no kill where it loses 80 — but
neither reaches 13% alone and their union reaches 14.6%.

**There is no margin, because there is no plateau.** The curve climbs steeply
straight through the point where kills start disappearing. Taking the asymmetric
description filter: 6.7% one step below the lossless threshold, 10.2% at it,
14.7% one step above — and that step costs a kill. A safety margin of one step
costs a third of the benefit.

**The kills that set the ceiling are real, so the ceiling is not judge noise.** I
read the six lowest-scoring kills under each filter. Every one is a
carry-forward test judged against a carry-forward defect — for instance
`test_the_decompose_command_writes_a_ledger_entry_and_a_second_run_carries`
against a defect about `Review` storing `pair_verdicts` without the ledger path
populating them. Those are correct kills. They score low because the test's
source and the defect's description are about the same mechanism in different
words, and cosine distance over either encoding does not close that gap.

This is DR-259's shape again — the decision record for the obligation-linking
prefilter, whose held-out check found no threshold that separated genuine merges
from spurious ones. I expected the difficulty not to transfer, on the grounds
that "is this test even about this code" is a cruder question than "do these two
obligations state the same requirement". **On this evidence it transfers.**

## 3. What is worth keeping regardless of the decision

**`input_type` moves the code-to-code comparison a lot.** Marking both the code
region and the test source as `document` excludes 10.6% where sending no
`input_type` at all excludes 3.2% — more than triple, on identical texts and the
same model. The description filter moves the other way and by less: 10.2% with
`query`/`document` against 12.3% with neither.

This is a fact about `voyage-code-3` that outlives this experiment, and the
product cannot currently use it: `ModelClient.build_embedding_request` sends
`model` and `input` only. Adding `input_type` would move the embedding request
key and orphan the recorded linking transcripts, so it should be done when
something needs it, not speculatively.

**`voyage-code-3` exists and takes `input_type` of `query` or `document`.** I
verified both against the live API on 2026-08-30; a third value returns a 400
naming the two accepted ones. Both were unverified beliefs in the plan that
produced this experiment.

## 4. What this does not settle

**One review, and the verdicts are our own judge's answers.** Every number here
measures agreement with ourselves on a single Gate 2 run over this repo's own
code. That is the right target for a prefilter — its only job is to avoid
skipping a pair the judge would have called a kill — but it is not evidence
about whether the judge is right.

**The thresholds are fitted to the data they are scored on.** Each best-lossless
threshold sits immediately below the weakest kill in this run, so the exclusion
shares are ceilings, not operating points. A held-out check against #315's
archetype labels would be needed before trusting any of them, and given how
tight the curves are I expect it to lower them rather than raise them. That
check was not run, because a 14.6% ceiling does not justify it.

**Cost is untouched by this.** The pair stage remains the expensive one: $3.51
of the run's $4.25 across 332 calls, of which $2.46 is output. Removing 14.6% of
pairs removes about 14.6% of the output, roughly 36 cents, plus a smaller share
of the input — the shared prefix stays whatever happens. The call count barely
moves, because exclusions are scattered across tests rather than emptying whole
requests.

## Recommendation

Judge every pair. Do not adopt any of these filters.

If the pair stage's cost has to come down, the levers left are ones this
experiment did not test: raising the judgements-per-request limit, which is what
actually sets the call count, or narrowing the pair set at its source by
enumerating fewer defects per obligation. Both change what the review asks
rather than filtering the answers, so both need their own measurement.
