# DR-314 — How a batch of (defect, test) pairs answers

**Issue:** #314 (child of #312) · **Status:** decided, piloted · **Date:** 2026-08-30

## The question

DR-312's resolved question 2 left one thing open for #314's Gate 1: not whether
to build a call graph — that is settled, it is out of scope — but **how a batch
of pairs answers**. Two arms, and DR-312 forbids settling it by argument.

- **Listing.** Each test names the defects it would catch. A defect the test does
  not name is taken to survive. Small response, and the list shape the model
  handles today. But a judgement the model quietly sheds is indistinguishable
  from one it decided survives, which silently un-covers a defect — DR-164's
  silent-filter trap.
- **Verdict.** Each test carries an explicit verdict for every offered defect.
  Shedding becomes detectable, because a missing entry is a missing entry. But
  this is the shape DR-173 measured losing 59% of correct mappings, and it grows
  the response, which never amortizes — the caching discount is input-only.

## Decision

**Take the verdict arm.** It has higher mean recall, its recall is four times
more stable across draws, and shedding is detectable. It costs about 1.4× in
dollars and about 2× in output tokens.

The deciding figure is **not** the mean — it is the spread. The listing arm's
recall moved by 4 labelled kills across three seeds; the verdict arm's moved by
1. An arm whose answer swings that far between draws has not earned a verdict
this pipeline will act on.

## The figures

13 archetype cases, 38 labelled defects, 68 pairs, 32 human-reviewed labelled
kills from #315's ground truth. Three seeds per arm; nothing else varied.

| arm | recall min | recall max | recall mean | kills/defect | shedding detectable | output tokens | cost per run |
|---|---|---|---|---|---|---|---|
| listing | 0.8438 | 0.9688 | 0.8958 | 0.842–0.921 | **no** | 823 | $0.0098 |
| verdict | 0.9375 | 0.9688 | **0.9479** | 0.816–0.895 | **yes** | 1670 | $0.0141 |

The verdict arm's **worst** seed (0.9375) beats the listing arm's mean (0.8958)
and two of its three seeds. Cost is taken from seeds 1 and 2; seed 0 replayed
from the single-seed run that preceded this one and cost nothing, which is a
property of the cache and not of the arm.

Raw per-case predictions are in `docs/experiments/pair-response-shape/findings.json`;
the script that produced them is `pilot.py` beside it.

## The finding that matters beyond the shape choice

**DR-173's failure mode did not reproduce, and that is evidence for DR-312's
central claim.** DR-173's forced-per-obligation-verdict pilot improved its
headline number by answering *no* more often, losing 91 of 153 correct mappings.
The guard metric exists to catch exactly that, and here it does not fire: the
verdict arm's mean predicted kills per defect (0.816–0.895) sits alongside the
listing arm's (0.842–0.921) rather than collapsing beneath it. The dense shape
gained recall without buying it with silence.

I believe the reason is the question, not the shape. DR-173's stage asked
whether a test was *relevant to* an obligation — a judgement with no fact of the
matter, which is the unanswerable question #312 exists to retire. This pilot
asks whether a test would *fail on* a concrete defect, which has an answer. That
is DR-312's premise, and this is the first measurement supporting it.

The consequence for #316, the cutover issue: the dense shape's cost is real and
was accepted here on a 68-pair sample. A production review has far more pairs, so
**the output-token multiple, not the recall, is what to watch as the pair count
grows.** It is measured per run and does not amortize.

## What it costs in production, measured

#314's own Gate 2 run is the first figure on a real review rather than a
fixture, and it is large. The pair stage issued **332 calls** and spent **$3.51
of that run's $4.25** — 1,398,868 prompt tokens and **546,143 output tokens**,
against 43 calls and $0.74 for the whole rest of the pipeline. Evidence:
`dogfood-logs/314-gate2-run1/output.log`.

Two deliberate decisions drive it, and both are recorded where they were made:
a verdict per offered defect (this record), and one request per test
(`defects/pair_mapping.py::_batches`, taken so the schema's cross product equals
the offered set rather than inviting answers the stage would have to drop).

**Output tokens are the number to watch, because they never amortize** — the
caching discount is input-only. This is the figure DR-312's resolved question 2
said would justify funding real reachability as its own issue if it came back
unacceptable, and it is the figure #316 inherits.

## What this pilot does not establish

- **The sample is small.** 32 labelled kills over 13 constructed fixtures. A
  single flipped edge moves recall by 3 points. Three seeds show the arms differ
  by more than they wobble; they do not put a confidence interval on either.
- **Batching is untested.** Every case fitted in one call, so nothing here
  measures what happens at DR-164's shedding limit, which is the regime where
  the verdict arm's detectability is supposed to earn its cost. The arms were
  compared on shape alone, deliberately, and that regime is now the thing to
  watch in the shadow comparison.
- **The defects were labelled, not enumerated.** Fed in from #315's ground truth
  so the enumerator is held constant at perfect and every difference measured
  belongs to the judge. Real runs will judge enumerated defects, which are worse.

## Related

DR-312 (the defect-first shape and this question's origin) · DR-173 (the recall
guard and the dense shape's earlier failure) · DR-164 (the shedding limit and the
silent-filter lesson) · DR-259 (the in-repo precedent for piloting a cheap gate
offline) · #315 (the labels this scores against) · #150 (provider variance on a
single draw).
