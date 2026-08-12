# Obligation de-duplication — experiment notes

Working notes for offline experiments on the linking stage
(`src/acceptance/requirement/linking.py`), which decides whether two obligations
state the same requirement. Written after DR-259 so the next experiment starts
from the method rather than rebuilding it.

**The decision record is `docs/DR-259-obligation-pair-prefilter.md`.** This file
is the *method and its traps*; that one is the conclusion and the evidence.

## What is here

- `linking_corpus.py` — reads recorded linking calls out of the transcript cache
  and reassembles them into sweeps. Run it directly for a survey of what the
  cache currently holds. Every experiment should start with this.

## The data, as of 2026-08-12

Over a 1,204-transcript cache:

```
172  _Verdicts        the linking stage
  2  _Links           the pre-#144 linking schema — NOT comparable
  1  <embedding>      voyage-3.5-lite, 46 texts, from #259's own run
```

Six sweeps carry 10+ obligations, together ~2,950 distinct pairs and ~83
model-confirmed merges. Every one of them attributes to committed dogfood logs,
so their task files are recoverable.

**Only one embedding transcript exists.** Any experiment needing vectors for the
other five sweeps will make live calls and should budget for it.

## Traps, each of which cost DR-259 real time

**1. The cache is not an archive.** Transcripts are evicted. DR-259 lost #244's
and #228's linking calls *mid-analysis* and could not recover them. **Copy what
you need somewhere durable before you start**, and re-run the survey rather than
trusting the numbers above.

**2. The response is a JSON string, not a dict.** `record["response"]` must be
`json.loads`-ed before reading `verdicts`. Read as a dict it yields nothing and
every pair silently looks unanswered — this produced a full wrong analysis pass
that was only caught because *every* verdict came back missing.

**3. Identify linking calls by response schema, never by prompt text.** The
phrase "de-duplicating a set of obligations" also appears in recommendation and
strength prompts whose content discusses de-duplication — #144's own task file
triggers it. Measured here, the text filter returns 180 calls where
`response_schema.name == "_Verdicts"` returns 172. A text key is also hostage to
the next prompt reword.

**4. A "sweep" is a task file, not a run.** Batches are grouped by shared
obligation ids, and repeated runs over one task file share them, so the groups
above merge runs: the 99-obligation sweep spans **eleven** #232 runs, the
24-obligation one spans seven #144 runs. DR-259 hit this and its headline figures
moved from 1,065 pairs / 31 merges to 1,008 / 30 once deduplicated. Use
`Sweep.distinct_pairs()`, which dedupes on pair content, before reporting
anything. **Separating individual runs is unsolved** — obligation ids are minted
per response (#231), so they are neither stable across runs nor reliably
distinct.

**5. Do not normalise distances per sweep.** Ranking pairs within their own sweep
performed *worse* than pooling raw distances (5.5% vs 3.2% of pairs to retain
every genuine merge). The absolute scale carries meaning across task files, which
is what makes one fixed default viable at all.

**6. Hubness corrections make it worse, all of them.** z-score against each
endpoint's profile, CSLS, and mutual rank were measured and all degrade. The
merge hubs are not geometric hubs — the obligation that took five merges ranks
4th of 24 by mean distance, and another that took three ranks 14th of 35. Raw
distance works *because* it is uncorrelated with the failure mode. This is also
where TF-IDF entered, as the IDF analogy behind these corrections; it was
rejected with them and is not a standing fallback.

**7. Embed exactly `description + observable_behavior`, space-joined.** That is
what the threshold is calibrated against, and it must match
`linking.embedding_text` in the product code. Changing what goes in moves every
distance and invalidates the default without changing it.

## Where the question actually stands

DR-259 shipped a prefilter at **0.10** cosine distance over `voyage-3.5-lite`.
Read its *Held-out check* section before assuming anything about that number,
because the original case for it does not survive:

- The calibration sample separated perfectly below 0.10 — 20/20 genuine merges
  kept, 10/10 spurious dropped.
- A **fifth, held-out task file** (#259's own Gate 1) carries a **genuine** merge
  at **0.2257**, and the nearest calibration *spurious* merge sits at **0.116**.
  The two overlap, so **no threshold both keeps every genuine merge and drops the
  spurious ones.** The clean separation was an artifact of a sample containing no
  cross-abstraction paraphrase.
- 0.10 therefore ships as the *under-merging* side of a real trade, not as a
  separator. At 0.25 the filter admits 9 of 10 spurious merges and stops being a
  quality filter at all.

**The labelling is the weak link.** DR-259's genuine-vs-spurious labels were
assigned after seeing the pairs in distance order, so they are plausibly
contaminated by the signal they validate. Two labels do not depend on that
judgement — those pairs were answered both `true` and `false` across runs of one
task file, which is a spurious-merge signal with no distance in it.

**What would settle it:** a blind re-label (pairs shuffled, distances and
verdicts stripped), or #211's link-precision measure, which is the project's own
answer to this class of question and is now load-bearing rather than optional.

## Adjacent open defects, if the experiment is about quality rather than cost

- **#242** — a spurious link *blocks* a correct merge; an inconsistent cluster
  merges nothing.
- **#223** — a spurious link *completes*, destroying a requirement's content.
  #259's Gate 1 added an instance where linking is *not* at fault: derivation
  emitted composites spanning two requirements, which the strict sameness test
  correctly refuses to merge with either part, so they survive forever.
- **#210** — over-merging.
- **#211** — link-precision measurement, the prerequisite for settling any of it.

#223, #242 and #210 may be one underlying problem seen from three sides; that is
noted on #223 and #242 and is worth settling before starting any of them.
