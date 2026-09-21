# #348 Gate 2, run 1 — run `6806443320874a62` — NOT clean

Verdict NO-MATERIAL-GAPS: 22 obligations addressed and strongly supported, 3
scope exclusions confirmed from code. Not clean, for two reasons.

## 1. `[separable]` — the experiment work under `docs/experiments/rank-prefilter/` — my wording

The findings update, the replay script and its logs are flagged as not required
by any obligation. That is accurate against the task file and wrong against the
issue: #348 says "Record the outcome in the rank-prefilter findings either way",
and the replay is how the first Acceptance item is demonstrated. The task file
left the documentation deliverable out. Fixed for run 2 with a Completion
expectations section at the spec §7.1 example's grain ("Implementation",
"Documentation update"), not a restated behaviour.

## 2. `[already_present] pairs-asked-about-count-per-defect/asked-count-excludes-unanswered-pairs` — tool defect

The enumerated defect says the per-defect "asked" count underreports because it
leaves out pairs skipped as already covered. The requirement is the opposite:
"how many of its pairs were asked about and how many were skipped by stopping
early" — two counts, and a skipped pair is by definition not asked. The
"defective behaviour" the enumerator wrote down IS the required behaviour, and
the already-present check then confirmed the code has it. It moved no rating
(the obligation is strongly supported), but it is a lead telling a reader the
code is wrong where it is right. Queued as a filing in `docs/DEFERRED.md`.

## Also observed, not blocking

- **One uncovered defect cost a third of the judgements.**
  `embedding-request-unchanged/ranking-uses-symmetric-default-instead-of-written-asymmetric-form`
  was asked about all 492 tests (of 1,524 asked in the whole run) and nothing
  catches it — correctly, since it belongs to a scope exclusion that is owed no
  test. That is the already-queued 2026-08-31 entry "Defects are enumerated for
  criteria that are owed no test, and nothing can ever use them"; this run gives
  it a cost figure.
- 3 pairs `UNANSWERED`, all on covered defects, so no rating depends on them.

## #348's third Acceptance item, on this fresh review

- Pairs asked: 1,524 of 31,085 a full sweep would ask (4.9%); 29,561 skipped.
- Judgements per covered defect (67 covered): **median 4**, mean 15.4, p90 38,
  max 124. The median bar (under 10, as amended on #348) is met.
- Pair stage: 397 calls, $0.7647. A full sweep over 31,085 pairs is not run
  here; scaled linearly by pairs it would be about $15.6, and at 40 judgements
  per call it needs at least 778 calls — estimates, not measurements.
