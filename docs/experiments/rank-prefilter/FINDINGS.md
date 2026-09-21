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
