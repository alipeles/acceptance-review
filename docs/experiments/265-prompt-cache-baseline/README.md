# Prompt-cache baseline — #265

Taken 2026-08-20 on `main` at `340f163`, over the local transcript corpus.
Corpus fingerprint `4b88f2b9e4aa49a0`: 1,632 priced chat completions,
12,866,413 prompt tokens, $15.5382 recorded.

```bash
.venv/bin/python docs/experiments/265-prompt-cache-baseline/cache_baseline.py
.venv/bin/python docs/experiments/265-prompt-cache-baseline/cache_baseline.py --json out.json
```

No model calls. It reads `.acceptance/cache/transcripts/` and nothing else.

## Headline

| | original (#265, 500 transcripts) | this run (1,637) |
|---|---|---|
| prompt tokens | 4,181,930 | 12,866,413 |
| cached | 146,688 (3.5%) | 667,136 (**5.19%**) |
| recorded cost | $5.0358 | $15.5382 |
| at full price | $5.1348 | $15.9885 |
| saved | $0.099 — 1.9% | $0.4503 — **2.82%** |
| calls caching nothing | 454 of 495 | **1,494 of 1,632** |

92% of calls cache nothing at all. The bimodality #265 reported holds.

## Why the number is solved and not read

No recording carries a cached-token count: `_extract_usage` only began keeping
`prompt_tokens_details` in #285 (`82e4ec7`), and every transcript in this corpus
predates it — the script reports `measured_share: 0.0`. So `cached` is solved out
of the cost identity, using litellm's own price table, which is the table that
produced `cost_usd` in the first place.

The script already prefers a recorded `cached_tokens` when one is present. As
runs made after #285 accumulate, `measured_share` rises; once it dominates, the
solve should be deleted rather than maintained.

## What the corpus can and cannot tell you

- **It is not reproducible elsewhere.** `.acceptance/cache/` is gitignored and
  machine-local. That is why `baseline-2026-08-20.json` is committed beside the
  script: the artifact is the finding, not the ability to recompute it. The
  `corpus.fingerprint` field distinguishes "the numbers moved" from "a different
  corpus was read".
- **It is a fleet average.** Many runs, task files and prompt generations over
  about a month — not one run's profile.
- **Most of it is dead.** Only 30.2% of prompt tokens were issued under a prompt
  still in the tree. A prompt edit re-keys its stage's requests and orphans the
  old records, and nothing evicts them.

## The two findings

**1. The one prompt that caches well is on a parked branch.** The two
discrimination clusters are the same stage under different prompt versions:

| cluster | calls | recorded | hit rate | matches `main`? |
|---|---|---|---|---|
| `main`'s prompt | 80 | 2026-07-23 → 08-12 | **0.2%** | yes |
| #191's prompt | 276 | 2026-08-12 → 08-13 | **25.4%** | no |

The second is `191-partition-discrimination`, whose notes report 84–93% of each
verdict request served from cache after putting the invariant block first and
per-batch content last. A ~100× difference on one stage, measured, unpushed.

**2. Three of the four biggest stages cannot cache on this model at all.**
OpenAI caches only prefixes of at least 1,024 tokens (verified against the
provider's documentation on 2026-08-20; it is model-dependent). Sibling calls in
test recommendation, unrequested-change detection and coverage classification
share only their system prompt — 278, 403 and 680 tokens. No ordering change
rescues a prefix that short; invariant content has to move above the variable
part until the shared prefix clears the floor.

Those three figures are **cross-run floors**, marked `?` in the output: they were
computed without a within-run marker, so a single run may share more. Mapping is
the one measured properly, grouped on `## Candidate tests`.

**Mapping is the counter-case, and the open question.** It already orders
correctly — `## Obligations` before `## Candidate tests`, every obligation
repeated in every call per DR-164 — and its shared prefix is 1,729 tokens, over
the minimum. It still cached on 3 of 464 calls. Neither ordering nor length is
the constraint there; temporal locality and byte-exactness of the prefix are what
remain, and the direct measurement is what settles it.

Consistent with the threshold reading, the three decompose clusters line up with
their prefix lengths: 2,196 tokens → 40.9%, 1,390 → 19.6%, 694 → 8.9%.

## Not covered here

- **`cache_control` appears nowhere in `src/` or `tests/`.** Anthropic-family
  models require explicit breakpoints, so any lever adopted is provider-specific
  and belongs behind the client abstraction — a point for #265's DR.
- Whether a cache hit can change a response: it cannot. Both providers state that
  caching does not affect output generation, and the finding is recorded on #265
  rather than here.
