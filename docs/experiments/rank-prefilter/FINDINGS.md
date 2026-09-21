# Ranking tests per defect — findings

**Kills sit at the top of the similarity ranking. Ranking each defect's judged
tests by voyage-code-4 description-to-test cosine, the median killed defect has
its first kill at rank 1 to 3, and the top 20 of ~166 to ~496 tests contain a
kill for 92.6% to 97.7% of killed defects, across all three labeled corpora.**
Judging only each defect's top 20 would ask about 4% to 12% of pairs. Unlike the
cosine thresholds that failed to transfer in `prefilter-committee`, a rank
cutoff is scale-free, and k = 20 performs consistently on corpora whose test
counts differ by 3x.

Method: `score_rank.py`, run 2026-09-21 against the #314 and #316 committee
corpora and the #340 Gate 2 review (18,410 pairs, 302 judge kills, 72 mutation
attempts), vectors from the recorded Voyage cache plus one fresh paced pass for
#340's texts. Full output in `score_rank.log`.

## First-kill rank and coverage

| corpus | killed defects | first-kill rank median / p90 / max | top-10 | top-20 | top-40 |
|---|---|---|---|---|---|
| #314 (166 tests) | 46 | 1 / 5 / 75 | 95.7% | 95.7% | 97.8% |
| #316 (496 tests) | 43 | 1 / 6 / 116 | 95.3% | 97.7% | 97.7% |
| #340 (282 tests) | 68 | 3 / 13 / 149 | 86.8% | 92.6% | 95.6% |
| #340 executed oracle (13 killed attempts) | 13 | 1 / 7 / 37 | 92.3% | 92.3% | 100.0% |

Coverage figures are defect-coverage@k: the share of killed defects with at
least one kill in the top k. That is the decision metric because
`defects/support.py` covers a defect at one kill; later kills do not change the
class. The executed oracle (tests that actually failed under a mutant) ranks at
least as well as the judge's kills, on an n of 13.

## The sparsity hypothesis, answered

The motivating guess was that a defect rarely has more than one or two killers.
**As stated, that is false for judge-recorded kills:** on #340, of 68 killed
defects, 10 have exactly one kill, 14 have two, and 44 have three or more;
#316 is denser still. Only #314 is sparse (22 of 46 with exactly one). What
survives, and is more useful, is the support-derivation fact above: however
many killers exist, *one* suffices for the rating, so the operative question is
how deep a judge must read in rank order before finding one, and the answer is
"a handful".

## What a rank-ordered judge would cost

The #340 static stage judged 18,410 pairs for $2.88. A top-20 head is ~1,440
pairs, roughly $0.25 to $0.35 at the same rates. Three options for the tail,
in increasing cost:

1. **Recorded rank-exclusion.** Miss rate is measured: 7.4% of killed defects
   on #340 (2.3% to 4.4% on the others) have no kill in the top 20. A missed
   first kill produces a false "unsupported", a false alarm rather than false
   assurance, but it is a real finding error and DR-173's recall guard applies.
2. **Cheap tail sweep as a promoter.** A cheap model (or Jev, whose ranking is
   the natural shadow candidate) reads the tail with one permitted effect:
   promoting a suspected kill into the judge's queue. A false promotion costs
   one judgement; misses are measurable on these corpora before trusting it.
3. **Judge everything, rank-ordered, stop early.** Since one kill covers, the
   judge can walk the ranking and stop after n confirming kills (n = 2 for
   redundancy against DR-180 instability). Killed defects stop at median rank
   2 to 6; only unkilled defects pay the full sweep, and an unkilled defect's
   sweep is exactly what an honest "unsupported" requires.

Option 3 is the conservative default: it changes no conclusion's evidence
basis, and on these corpora most defects are killed, so most sweeps stop
early. Options 1 and 2 stack on it for the unkilled minority if their cost
still matters.

## Re-score without `input_type` (#348's first task), 2026-09-21

**The ranking holds without Voyage's `input_type`, so #348 builds on symmetric
embeddings and `build_embedding_request` stays untouched.** The figures above
used the asymmetric form (description as `query`, test as `document`), which
the product's embedding request cannot send without moving its request key and
orphaning the recorded linking transcripts (`pair-prefilter/FINDINGS.md` §5).

`score_rank.py` was first ported off the cloud machine's paths and re-run in
the asymmetric form on this machine. It reproduced every committed figure
above exactly (`score_rank-asymmetric-local.log`), so the symmetric run
(`score_rank-symmetric.log`, `--symmetric`) is compared like for like.

| corpus | top-20 coverage, asymmetric | top-20 coverage, symmetric | difference |
|---|---|---|---|
| #314 | 95.7% | 97.8% | +2.1 |
| #316 | 97.7% | 95.3% | −2.4 |
| #340 | 92.6% | 94.1% | +1.5 |
| #340 executed oracle | 92.3% | 92.3% | 0 |

The bar was "within about two points". Two corpora improve and one falls by
2.4, which on #316's 43 killed defects is exactly one defect (one in 43 is
2.3 points). The mean moves by +0.4. First-kill median rank is unchanged on
every corpus (1, 1, 3).

## The two-kill stop rule does not meet #348's "under 10 judgements" bar

The port added a measure the first run lacked: how many judgements a judge
walking the ranking issues before it has seen `stop` kills for a defect, or the
whole list if it never does. Symmetric figures (asymmetric in the log, and
no better):

| corpus | stop after 1 kill: judgements issued / mean per covered defect | stop after 2 kills: judgements issued / mean per covered defect |
|---|---|---|
| #314 | 40.0% / 3.7 (46 defects stop early) | 71.4% / 17.6 (24 stop early) |
| #316 | 11.3% / 4.7 (43) | 20.5% / 10.4 (39) |
| #340 | 8.9% / 7.5 (68) | 26.6% / 21.1 (58) |

Two effects, and the first is the larger. **A defect with exactly one
recorded kill never reaches a second, so under a two-kill rule it pays the full
sweep** — 22 of #314's 46 killed defects, 10 of #340's 68. And the mean per
covered defect is pulled up by a long tail: the medians at two kills are 4, 4
and 7. With one kill, every killed defect stops early and the means fall to
3.7 to 7.5.

The share of judgements issued is over *all* pairs, so it includes the full
sweeps of unkilled defects (29 of #314's 75, which is why #314 stays at 40%
even at one kill).

## The product's own embedding model is enough

Everything above embeds with `voyage-code-4`. The product's configured
embedding model is `voyage-3.5-lite` (`config.py::DEFAULT_EMBEDDING_MODEL`),
which the linking stage already uses. Scored the same way, symmetric
(`score_rank-symmetric-voyage-3.5-lite.log`, `--model voyage-3.5-lite`):

| corpus | top-20 coverage, code-4 / 3.5-lite | stop after 1 kill: mean judgements per covered defect, code-4 / 3.5-lite |
|---|---|---|
| #314 | 97.8% / 100.0% | 3.7 / 2.8 |
| #316 | 95.3% / 90.7% | 4.7 / 7.4 |
| #340 | 94.1% / 92.6% | 7.5 / 7.6 |

The general model ranks a little worse on #316 and no worse elsewhere, and
under a one-kill stop rule it stays under 10 judgements per covered defect on
all three corpora.

**Coverage@k matters less here than it did for a cutoff.** A judge that walks
the ranking until it records a kill asks about every test of a defect that has
none. A worse ranking costs extra judgements; it cannot change a rating. So the
model choice is a cost question, and on these corpora the cost difference is
small. #348 ranks with the configured embedding model, and adds no setting
for a second one.

## Replaying the built walk over two recorded reviews (#348's first Acceptance item)

`replay_stop_rule.py` feeds each review's recorded verdicts through the
product's own `rank_pairs` and `_walk_ranked` (stop after 1 kill, rounds of 4
tests per defect doubling each round, `voyage-3.5-lite`), and compares every
criterion's class, covered count and unknown count against the full sweep.
Output in `replay-340.log` and `replay-45-run3.log`.

| review | criteria that differ | pairs asked, of the full sweep | mean / median judgements per covered defect | first-kill rank mean / median / p90 / max |
|---|---|---|---|---|
| #340 (`07d61a8`) | 0 of 28 | 1,968 of 18,419 (10.7%) | 12.4 / 4 | 7.6 / 2 / 19 / 91 |
| #45 run 3 (`82b29b5`) | 0 of 33 | 9,524 of 50,540 (18.8%) | 49.5 / 4 | 34.6 / 4 / 90 / 452 |

**Every rating is identical, as it must be by construction.** The saving is
81% and 89% of the pair judgements.

**The "under 10 per covered defect" bar is missed, for two reasons:**

1. **Growing rounds overshoot.** A kill at rank 5 is found in the second round,
   which asks ranks 5 to 12. Against stopping exactly at the first kill:

   | round policy | #340 mean | #45 mean | sequential rounds to sweep a defect, #340 / #45 |
   |---|---|---|---|
   | stop exactly (1 test per round) | 7.6 | 34.6 | 282 / 532 |
   | fixed 4 | 9.5 | 36.4 | 71 / 133 |
   | 4, then ×1.5 | 10.8 | 44.0 | 9 / 11 |
   | 4, then ×2 (built) | 12.4 | 49.5 | 7 / 8 |

2. **On #45 even a perfect stop misses it.** The first kill's mean rank is 34.6
   there, against a median of 4: a minority of defects have their first kill
   deep in the ranking (p90 90, max 452), and a mean over covered defects is
   dominated by them. #45's first-kill tail is much longer than the three
   corpora the ranking was measured on (#340's p90 is 19).

The median is 4 on both reviews under every policy. A bar stated as a mean
over covered defects measures the tail of the ranking, not the typical
defect.

## Caveats

- The oracle for #314/#316/#340 rankings is the pair judge's own kills, noisy
  per DR-180. The executed oracle agrees but is 13 defects.
- Early stopping interacts with DR-314's every-pair-accounted discipline: a
  skipped pair must be recorded as "not judged: defect covered at rank r",
  never silently absent.
- The existence prior stays out of the judge's prompt. Ranking allocates
  attention; the judge still answers the cold existential question, and an
  unkilled defect remains a first-class outcome.
- k and the stop rule are configuration, tuned on these three corpora;
  adoption confirms on the next fresh review, per the standing protocol.
