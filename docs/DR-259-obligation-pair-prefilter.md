# DR-259 — Prefilter obligation pairs by cosine distance

**Issue:** #259 (child of #181) · **Status:** decided, not yet implemented ·
**Date:** 2026-08-11

## The question

`link_duplicate_obligations` asks the model about every admissible pair of
obligations, quadratically — 399 pairs on a 35-obligation decomposition — and
the answer is `false` for almost all of them. Can most pairs be eliminated
before the call, and if so, on what measure and at what threshold?

## Decision

**Prefilter on raw cosine distance between embeddings of the two obligations,
default threshold 0.10, configurable.** Pairs above it are never asked.

The threshold is scale-specific to `voyage-3.5-lite`; a different embedding
model needs recalibration, not this number. Erring low is deliberate: a pair
wrongly filtered out costs one redundant obligation, while a spurious pair
handed to the model can be merged, and a wrong merge destroys a requirement
silently. `linking.py` already declares that direction load-bearing.

## How the data was obtained

The measurement is offline, over **recorded linking transcripts** in
`.acceptance/cache/` — no live calls beyond the embeddings.

Transcripts carry no run label, so linking calls were grouped into sweeps by
shared obligation ids. Within one sweep batches share 20+ obligations; across
sweeps they share 1–2 (slug collisions), and that gap separates cleanly. Each
group was then attributed to a dogfood run by matching against the obligation
ids in its committed `output.log`.

**Validation:** the method was checked against a full replay of
`248-gate1-run3`, which reproduced its 26 obligations, 181 asked pairs and 0
merges exactly.

Four sweeps were usable: `#248 run2`, `#248 run3`, `#232 run3`, `#144 run3`.
**#244 and #228 could not be used** — their linking transcripts are no longer
in the cache, which is itself worth knowing: the cache is not an archive, and
an experiment that depends on it should be run against committed dogfood logs
while the transcripts still exist.

### Two corrections made during the analysis

Both are recorded because the uncorrected figures were quoted before they were
caught, and because each is a trap for the next person doing this.

1. **Per-sweep percentile normalisation was wrong.** Ranking pairs within their
   own sweep performed *worse* than pooling raw distances (5.5% vs 3.2% of
   pairs to retain every genuine merge). The absolute distance scale carries
   meaning across task files, which is what makes a single fixed default
   viable.
2. **`144-gate1-run3`'s group conflates three runs of one task file** — 33
   calls where 11 are expected, 275 pair ids over 218 distinct pairs. Counts
   were deduplicated on pair content. Headline figures moved from 1,065 pairs /
   31 merges to **1,008 distinct pairs / 30 distinct merges**; the separation
   and the chosen threshold did not move.

## Findings

### The separation

Distances over `description + observable_behavior`, embedded with
`voyage-3.5-lite`. Of the 30 confirmed merges, 20 read as genuine duplicates
and 10 as spurious links (see the table below).

The farthest genuine merge sits at **0.0938**; the nearest spurious one at
**0.1155**. Every threshold in that band keeps all 20 genuine merges and drops
all 10 spurious ones.

| threshold | pairs asked | genuine kept | spurious admitted |
|---:|---|---|---|
| 0.080 | 2.1% | 17/20 | 0/10 |
| 0.094 | 2.8% | 20/20 | 0/10 |
| **0.100** | **3.1%** | **20/20** | **0/10** |
| 0.115 | 4.5% | 20/20 | 0/10 |
| 0.130 | 6.3% | 20/20 | 1/10 |
| 0.200 | 24.7% | 20/20 | 8/10 |

Per sweep at 0.10, every genuine merge is retained and every spurious one
dropped:

```
#248 run3 (accepted)   ask   2/181  (1.1%)    0/0  genuine merges retained
#248 run2              ask  17/399  (4.3%)   12/12 retained
#232 run3              ask   7/210  (3.3%)    4/4  retained
#144 run3              ask   6/275  (2.2%)    5/5  retained
```

`#248 run3` — the decomposition actually accepted at Gate 1 — produced **zero
merges across 181 asked pairs**. On that run the filter is pure saving with
nothing at risk.

### What the filter removes is disproportionately defect

The farthest confirmed merge, at 0.374, is #223's documented instance:
`preserve-decomposition-accuracy-measurement` merged with
`single-obligation-yield`, on a stated reason that attributes to the first a
claim it does not make. Six of the ten spurious merges attach to a single
"hub" obligation, `linked-obligation-for-two-sections`, which absorbed five
different partners in one run.

### Independent corroboration of two spurious labels

Two pairs were judged **both `true` and `false`** across runs of the same task
file, and both are in the spurious group:

- `linked-obligation-for-two-sections` + `linked-obligation-preserves-union-of-provenance`
- `uncertain-duplicates-remain-separate` + `stable-links-unless-derived-obligations-change`

This is #180/#193 instability, and it is a spurious-merge signal with no
distance in it — so for those two the label does not rest on the judgement
being validated.

## Rejected alternatives

**Hubness corrections — rejected, they make it worse.** The concern was that a
"hub" obligation close to everything would drag pairs in, and that normalising
by each endpoint's own neighbourhood would discount it (the TF-IDF/IDF
analogy). Measured, all three variants degrade:

| measure | AUC (spurious > genuine) | pairs asked to retain all genuine |
|---|---|---|
| raw cosine | 1.000 | 2.6% |
| z-score against each endpoint's profile | 1.000 | 6.0% |
| CSLS, k=5 | 0.995 | 6.6% |
| mutual rank | 0.995 | 7.3% |

The reason is that **the merge hubs are not geometric hubs.**
`linked-obligation-for-two-sections` took 5 merges but ranks only 4th of 24 by
mean distance to all others; `exact-field-equality-for-repeat` took 3 and ranks
14th of 35 — exactly average. Mean distance varies ~11% across obligations
while pair distance varies 0.04–0.99, so normalising by it adds noise and
removes almost no bias. Raw distance works *because* it is uncorrelated with
the failure mode; coupling it to the model's own notion of centrality would
throw that away.

**A stdlib TF-IDF cosine — viable, not chosen.** Word uni/bigrams plus char
4-grams separated just as cleanly (gap 0.646–0.773, 3.3% of pairs) and agreed
with the embeddings on near-vs-far for all 30 merges. It needs no provider, no
key, and no record/replay handling, which makes it the cheaper option on every
axis except semantic generality. Embeddings were chosen deliberately; if the
provider dependency later proves awkward, this is the fallback and it is known
to work on this evidence.

## Limits

**The threshold is calibrated on labels that are not independent.** The 30
pairs were labelled genuine-vs-spurious by reading them *after* seeing them
ordered by distance, so the labelling is plausibly contaminated by the signal
it validates. A perfect separation on a hand-labelled n=30 produced that way is
partly an artifact of method. What would settle it:

- a **blind re-label** — the pairs shuffled, distances and verdicts stripped,
  judged cold; or
- scoring through **#211**'s link-precision measure, which is the project's own
  answer to this class of question.

**Sample is three task files, all this repo's own**, which share vocabulary far
more heavily than arbitrary client mandates would.

**`linking.py` asserts a precondition this change breaks:** *"If the obligation
count later forces partitioning, #211's link-precision measure needs to exist
first, so the loss is measured rather than assumed small."* A prefilter makes
that same trade. Proceeding ahead of #211 is a choice to record, and the
docstring must be updated in the same change so the code stops asserting a rule
it no longer follows.

## Evidence — the 30 distinct confirmed merges

Ordered by voyage distance. ⚠ marks a pair judged both ways across runs.

| voyage | lexical | read as | run | A | B |
|---:|---:|---|---|---|---|
| 0.001 | 0.083 | genuine | #248 | `byte-identical-review-state` | `byte-identical-review-state-2` |
| 0.005 | 0.038 | genuine | #232 | `byte-identical-inputs-byte-identical-review-state` | `byte-identical-input-byte-identical-review-state` |
| 0.009 | 0.108 | genuine | #248 | `no-live-model-calls-in-tests` | `tests-no-live-model-calls` |
| 0.011 | 0.169 | genuine | #232 | `no-preserve-property-reason-for-no-obligation` | `no-obligation-reason-is-non-preservational` |
| 0.013 | 0.057 | genuine | #248 | `no-repeat-earned-suffix-on-survivor` | `no-repeat-earned-suffix` |
| 0.028 | 0.335 | genuine | #248 | `exact-field-equality-repeat` | `exact-field-equality-for-repeat` |
| 0.028 | 0.197 | genuine | #144 | `byte-identical-review-state-for-identical-input` | `deterministic-review-state` |
| 0.036 | 0.372 | genuine | #248 | `field-difference-keeps-obligation` | `field-difference-keeps-obligation-2` |
| 0.043 | 0.451 | genuine | #144 | `links-stable-when-derived-obligations-unchanged` | `stable-links-unless-derived-obligations-change` |
| 0.045 | 0.515 | genuine | #144 | `prelink-derivation-persisted-in-review-state` | `persist-pre-link-derivation-state` |
| 0.051 | 0.338 | genuine | #248 | `surviving-obligation-content-preserved` | `survivor-content-unchanged` |
| 0.057 | 0.483 | genuine | #232 | `acceptance-criterion-test-yields-test-obligation` | `test-demand-becomes-obligation-demand` |
| 0.061 | 0.086 | genuine | #248 | `repeat-dedup-recorded-as-shape` | `repeat-recorded-as-shape` |
| 0.064 | 0.518 | genuine | #248 | `head-repeat-counts-as-one` | `repeat-head-counts-as-one` |
| 0.066 | 0.457 | genuine | #248 | `first-and-remainder-deduplication` | `repeat-head-counts-as-one` |
| 0.071 | 0.184 | genuine | #248 | `only-head-repeat-is-merged` | `repeat-only-at-head` |
| 0.080 | 0.374 | genuine | #232 | `behaviour-and-test-distinct-requirements` | `behavior-obligation-and-test-obligation-remain-distinct` |
| 0.082 | 0.481 | genuine | #144 | `reason-clause-counts-as-same-requirement` | `reason-clause-counts-as-same-requirement-2` |
| 0.087 | 0.609 | genuine | #248 | `yielded-requirement-never-empty` | `nonempty-yield` |
| 0.094 | 0.646 | genuine | #248 | `first-and-remainder-deduplication` | `head-repeat-counts-as-one` |
| 0.116 | 0.788 | **spurious** | #248 | `repeat-head-counts-as-one` | `exact-field-equality-for-repeat` |
| 0.144 | 0.805 | **spurious** | #248 | `first-and-remainder-deduplication` | `exact-field-equality-for-repeat` |
| 0.156 | 0.789 | **spurious** | #144 | `linked-obligation-for-two-sections` | `surviving-obligation-named-by-all-requirements` |
| 0.165 | 0.773 | **spurious** | #232 | `behaviour-and-test-distinct-requirements` | `test-demand-becomes-obligation-demand` |
| 0.175 | 0.815 | **spurious** | #144 | `linked-obligation-for-two-sections` | `reason-clause-counts-as-same-requirement-2` |
| 0.182 | 0.779 | **spurious** | #144 | `linked-obligation-for-two-sections` | `reason-clause-counts-as-same-requirement` |
| 0.183 | 0.782 | **spurious** ⚠ | #144 | `linked-obligation-for-two-sections` | `linked-obligation-preserves-union-of-provenance` |
| 0.185 | 0.858 | **spurious** | #144 | `linked-obligation-for-two-sections` | `distinct-requirements-not-merged-by-vocabulary` |
| 0.201 | 0.851 | **spurious** ⚠ | #144 | `uncertain-duplicates-remain-separate` | `stable-links-unless-derived-obligations-change` |
| 0.374 | 0.935 | **spurious** | #248 | `preserve-decomposition-accuracy-measurement` | `single-obligation-yield` |

Related: #259, #181, #211, #242, #223, #210, #144, #180, #193.
