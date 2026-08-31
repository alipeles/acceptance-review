# Pair response-shape pilot (#314)

Which response shape the (defect, test) pair question uses. **The decision and
its figures are `docs/DR-314-pair-response-shape.md`;** this file is how to
repeat the measurement and the traps in it.

## Running it

```bash
.venv/bin/python docs/experiments/pair-response-shape/pilot.py
```

Makes live calls — 624 of them, and records them, so a second run replays and
costs nothing. Roughly $0.86 from cold. Four arms are drawn nine times and four
three; `DEEP_SEED_ARMS` says which and why. Writes
`findings.json` beside the script, holding every per-case prediction as well as
the aggregate figures, so a disagreement with the write-up can be traced to the
case that caused it.

## What it measures against

#315's human-reviewed defect labels on the archetype fixtures. Each labelled
defect carries `killed_by`, the tests that would fail if the delivered code
contained it. That is the ground truth; the arms are scored on how well their
predictions match it.

**This is a stronger control than #314's acceptance asks for.** #314 names the
current mapping stage's shared-mapping count, which compares one model stage's
opinion against another's. The labels compare against a human's.

## Traps

**The labelled defects are fed in, not enumerated.** Deliberate: #315 exists to
separate "the enumerator missed the defect" from "the judge missed the kill",
and this pilot chooses a shape for the judge. Holding the enumerator at perfect
means every difference measured belongs to the judge. It also means the recall
figures here are an upper bound on what a real run achieves.

**Every arm sends identical request content**, except `tagged-alias`, which has
to rewrite the ids to be the arm it is. Otherwise only the per-arm instruction
and the response schema differ. If you change a prompt, change it in
`_SHARED_PROMPT` so every arm moves together, or the comparison stops being
attributable.

**One draw decides nothing, and three decided something wrong.** The single-seed
version of this pilot showed 0.875 against 0.9375 and would have been fairly
dismissed as noise. Three seeds separated the original two arms. But three seeds
also made `kills-only` look like the best arm here when nine show it is the worst
of the four still in contention — see *Three draws decided nothing* below. Vary
only the seed; temperature and prompts stay fixed.

**Seed 0 may replay for free.** It was recorded by the earlier single-seed run,
so its `cost_usd` reads $0 and is not comparable with the other two. Take cost
from seeds 1 and 2, or clear the cache first. **`evidence_cost_usd` is the field
that does not have this problem** and is what the 2026-08-30 section below uses:
`cost_usd` is what *this* run was billed, so every arm reads $0 once it is
recorded, while `evidence_cost_usd` counts a replayed call at its recorded cost.
The old field is still written, and still carried forward from the previous
`findings.json` rather than overwritten with a zero, so DR-314's quoted figures
stay traceable.

**Node ids must match the labels.** `killed_by` uses `<file>::<name>` pytest node
ids, and the script parses tests into the same form. If a label names a test the
parser does not produce, that labelled kill silently becomes unreachable and
both arms lose recall for a reason that is not about either of them. The probe
that checks this is the id-matching assertion — run it after touching either
side.

## Sample size

13 cases, 38 defects, 68 pairs, 32 labelled kills. One flipped edge moves recall
by about 3 points. Enough to separate the arms; not enough for a confidence
interval on either.

---

## Tagged-reason and alias arms — 2026-08-30

**`union` is the arm to take: on nine draws each it beats the shipped shape on
every recall figure and costs 18% less.** Neither tag arm qualifies and the alias
arm fails outright. `kills-only` looked like the winner on three draws and is not
one on nine — that reversal is the most useful thing in this section and is
written up under *Three draws decided nothing* below. The six arms below were
added to attack the cost DR-314's shape turned out to carry on a real review: #314's Gate 2 run spent 546,143 output tokens
($2.46) on the pair stage, of which roughly 44% was defect-id echoes, 32% was
reasons and 23% was JSON scaffolding. The thesis was that most survives reasons
compress to a relation tag with no information lost, and that id echoes compress
to per-batch aliases. The first half is true about the judgements and false about
the tokens. The second half costs recall outright. What did work was not
compressing the survives reason but declining to ask for it.

### What was added

`reasoned` is a baseline, not a candidate. **The verdict arm is not the shipped
shape** — the pilot's `_Verdicts` carries `defect_id` and `fails` and nothing
else, while `defects/pair_mapping.py::_Judged` carries a `reason` as well. A
ratio taken against the verdict arm therefore measures a reason that shipped code
already pays for, so `reasoned` reproduces the shipped schema exactly and is the
denominator for every saving quoted here. Ratios to the verdict arm are given
too, because that is the arm DR-314 chose.

`tagged` adds a `relation` field carrying a closed enum, with `reason` left empty
wherever a relation fits. `tagged-single` carries the same relation inside the
existing `reason` field and changes nothing else about the schema.
`tagged-alias` is `tagged` plus per-batch `D1`/`T1` aliases, presented beside the
full ids in the request and admitted alone by the response schema. `kills-only`
keeps the shipped schema and asks for a reason only where the test fails, leaving
it empty where the test survives. `union` returns a union of two per-disposition
entries, so a surviving pair carries no `reason` field at all rather than an
empty one. The last two were added after the first four had run and pointed at
them.

The enum came from the 12,323 survives reasons the Gate 2 run recorded in
`docs/experiments/pair-prefilter/survives-reasons.tsv`. A crude regex pass puts
73.3% of them in five relations — NOT-ASSERTED 44.2%, NOT-EXERCISED 21.7%,
SCOPE-ONLY 7.3%, WRONG-LAYER 0.1%, STUBBED 0.03% — and the unmatched 26.7% is
mostly the same three relations phrased differently rather than a sixth relation.

### The figures

13 cases, 38 labelled defects, 68 pairs, 32 human-reviewed labelled kills,
nothing varied but the seed. The four arms still in contention are drawn nine
times; the four already decided keep their three. **`n` is in the table because
`min` is not comparable across different `n`** — a minimum over nine draws is
systematically lower than a minimum over three — so compare the four nine-seed
arms on mean, median and how often they fall below the bar, and read the
three-seed rows as decided rather than as measured to the same standard.

| arm | n | recall min–max | mean | median | kills/defect | out tokens | ×reasoned |
|---|---|---|---|---|---|---|---|
| listing | 3 | 0.8438–0.9688 | 0.8958 | 0.8750 | 0.842–0.921 | 823 | 0.28 |
| verdict | 9 | 0.9375–0.9688 | 0.9514 | 0.9375 | 0.816–0.895 | 1670 | 0.57 |
| reasoned (shipped) | 9 | 0.9062–0.9375 | 0.9271 | 0.9375 | 0.789–0.816 | 2921 | 1.00 |
| kills-only | 9 | 0.8750–1.0000 | 0.9410 | 0.9375 | 0.763–0.895 | 2600 | 0.89 |
| **union** | 9 | 0.9062–1.0000 | **0.9688** | **0.9688** | 0.789–0.868 | 2404 | **0.82** |
| tagged | 3 | 0.9375–0.9688 | 0.9479 | 0.9375 | 0.816–0.842 | 2808 | 0.96 |
| tagged-single | 3 | 0.7500–0.9688 | 0.8750 | 0.9062 | 0.711–0.842 | 2522 | 0.86 |
| tagged-alias | 3 | 0.6250–0.6875 | 0.6667 | 0.6875 | 0.579–0.605 | 2204 | 0.75 |

Draws falling below the bar of 0.9375, which is the `verdict` arm's worst of nine:
`verdict` 0 of 9, `union` 1 of 9, `kills-only` 2 of 9, `reasoned` 3 of 9.

Projected onto the Gate 2 pair stage by carrying each arm's ratio to `reasoned`
across: `tagged` saves $0.10 of $2.46, `kills-only` $0.27, `tagged-single` $0.34,
`union` $0.44, `tagged-alias` $0.60, and the reason-free `verdict` arm $1.05. No
pair was left unanswered by any arm, and no alias failed to decode. Every arm
told to write no prose about a surviving pair complied on 100% of survives
verdicts, except `tagged-alias` at 89.1–100%; `tagged-single` wrote into the
field by design. The `union` arm returned the no-reason shape on all 321 of its
surviving pairs across its nine seeds, so the union discriminated cleanly and
nothing had to be repaired locally.

### The qualification verdict

**Which bar applies depends on which question is being asked, and both are
reported.** DR-314's rule — worst-seed recall not below the `verdict` arm's
worst, and predicted kills per defect not beneath its range — was written to
choose between two arms at the outset, with nothing yet shipped. The question
here is different: whether to *replace* a shape already in the code. For that the
incumbent is `reasoned`, and the test is whether a candidate is at least as good
as it. Read against DR-314's original bar, **no arm here qualifies, including the
shipped shape itself, which falls below 0.9375 on 3 of its 9 draws.** That is the
clearest sign the original bar is answering a question nobody is now asking.

**`union` beats the shipped shape on every recall figure and costs 18% less.**
Mean 0.9688 against 0.9271, median 0.9688 against 0.9375, best draw 1.0000
against 0.9375 — the shipped arm never reaches 0.9688 on any of its nine draws,
which is `union`'s median. It falls below the bar on 1 draw of 9 where the
shipped shape falls below on 3. Its predicted kills per defect (0.789–0.868) has
the same floor as the shipped shape's (0.789–0.816) and a higher ceiling, so
DR-173's failure mode is not present. The one figure where the shipped shape
leads is spread — 0.0312 against 0.0938 — but it is tight around a lower value,
and a shape that never exceeds 0.9375 is not stability worth keeping.

The mechanism worked as intended: the no-reason shape came back on all 321
surviving pairs across nine draws, so the judge discriminated the union cleanly
and nothing had to be repaired locally.

**`kills-only` is not the winner, though three draws said it was.** Over nine its
mean falls to 0.9410, its spread is the widest of the four nine-seed arms
(0.1250), its worst draw is 0.8750, and its guard metric floor drops to 0.763 —
beneath the shipped shape's. It still beats the shipped shape on mean and on
cost, so it is a live fallback if `union`'s schema change is unwanted, but it is
worse than `union` on every recall figure and saves less.

**`tagged` passes the bar and fails its purpose.** Worst-seed recall 0.9375,
exactly the verdict arm's worst; kills per defect 0.816–0.842, inside the verdict
arm's range; a relation was used on 100% of survives verdicts across all three
seeds. It saves 4% of output. **The compression thesis is right about the
judgements and wrong about the tokens, and the reason is scaffolding rather than
the idea.** A second field costs a key, an enum value, a second key and an empty
string on every surviving pair — `"relation":"NOT-EXERCISED","reason":""` is 38
characters where the sentence it replaced averaged 55, and where carrying the
same relation in the existing field is 23. Verified by reading the recorded
responses, not inferred from the totals.

**`tagged-single` removes that scaffolding and buys instability.** Same relations
in the existing `reason` field, 14% off the output, and recall of 0.7500 on seed
0 against 0.9688 on seed 1 — a seven-edge swing between draws. That is the same
instability DR-314 rejected the listing arm for, at four times the size, and its
kills per defect falls to 0.711, beneath the verdict arm's floor. Rejected.

**`tagged-alias` fails hardest and fails cleanly.** Recall 0.6250–0.6875, far
under the bar, with kills per defect at 0.579–0.605 — well beneath the verdict
arm's range. **This is DR-173's failure mode reproducing and the guard metric
catching it.** Precision stays at 0.909–0.957, so the arm is not answering wrong;
it is answering *no* more often and finding a third fewer kills. Nothing
mechanical explains it: every alias decoded, no pair went unanswered, and the arm
differs from `tagged` only in how ids are written. The judge reasons worse about
`D1` and `T1` than about names that mean something. Rejected.

### Where the survives reason's cost actually sits

**An empty field is not a free field, and that is why `kills-only` saves 10%
rather than the 32% the Gate 2 composition suggested.** Solving across the three
arms that share the shipped schema — 68 pairs each, about 32 of them kills — a
written reason costs 18.5 output tokens and an empty `reason` key costs 10.0, so
declining to write one recovers only 46% of what that field costs. Per pair:
`verdict` 24.6 tokens, `kills-only` 38.6, `reasoned` 43.1.

The consequence is structural rather than a matter of prompting. `StrictResponseModel`
forbids optional fields, because OpenAI strict mode has no notion of one — the
docstring on `llm.py::StrictResponseModel` says so directly. So a reason that is
present-but-empty is the *most* a per-entry instruction can achieve, and the
remaining 54% cannot be reached by asking. The `verdict` arm gets it only by
removing the field from the schema for every entry, which also removes the reason
on killing pairs that `report.py` renders to the reader.

**The `union` arm gets most of the rest, and it works.** A surviving pair returns
`defect_id` and `fails` alone; a killing pair returns those plus `reason`; the
field is absent rather than empty. `requirement/obligations.py` already returns a
union of per-disposition shapes and `supplied_ids.py::_constrained_nested` walks
union members so the id constraint survives, so no new machinery was needed —
and the constraint does survive: both members carry the supplied-id enum on
`defect_id`, which I checked on the generated schema before running anything.
Discrimination is by `Literal[True]`/`Literal[False]` on `fails` rather than by
which keys happen to be present, so a surviving entry that carried a reason
anyway would fail validation rather than be quietly accepted. None did.

It costs 2404 output tokens against `kills-only`'s 2600 and `verdict`'s 1670, so
removing the empty key recovered about 200 of the roughly 360 tokens those empty
keys cost. What remains above `verdict` is the reason on killing pairs, which is
the thing being kept deliberately.

### Tag usage

A relation fitted essentially every survives verdict — 100% in `tagged`,
92.7–100% in `tagged-single`, 89.1–100% in `tagged-alias` — so the enum is not
where any of these arms failed. But **two relations carry all of it**:
NOT-ASSERTED and NOT-EXERCISED account for all 110 survives verdicts in the
`tagged` arm. SCOPE-ONLY was never chosen by any arm across nine arm-seeds,
STUBBED was chosen three times and WRONG-LAYER never. A three-value menu would
have done the same work, and the offline corpus pass agrees: those same two
relations are 65.9% of the 12,323 recorded reasons and SCOPE-ONLY only 7.3%.

### What these figures do not establish

- **Defect ids here are a third of production length** — 24.2 characters across
  the 38 labelled defects against 76.5 across the Gate 2 corpus. Aliasing saves
  what an id costs, so `tagged-alias`'s 25% output saving is a floor rather than
  a reading, and its real saving would be larger. It fails on recall regardless,
  so this does not rescue it; it does mean the *cost* half of that row understates
  the arm.
- **The sample is 32 labelled kills over 13 constructed fixtures**, so one flipped
  edge moves recall by about 3 points. `union` leads the shipped shape by 1.3
  edges on the mean of nine draws and by 10 on the median. The mean gap is inside
  the noise a single draw carries; the median gap and the 3-of-9 against 1-of-9
  count of sub-bar draws are what the recommendation rests on, not the mean.
- **Adopting any of these re-judges every recorded verdict once.** All six change
  the request, so the pair stage's transcripts orphan and the carry key moves —
  roughly $3.50 one-off at the Gate 2 run's size, against `union`'s $0.44 a run,
  so it pays back in about eight reviews. `union` also changes the *response
  schema*, so `_ask` in `defects/pair_mapping.py` has to read two entry shapes,
  the persisted `PairVerdict.reason` arrives empty on surviving pairs — which
  `report.py` and `derive_support` have not been checked against — and it
  contradicts #314's own mandate, whose constraint "what comes back about a
  judged pair is which pair it is, its verdict, and a short reason" is pinned by
  `tests/defects/test_pair_mapping.py::test_the_answer_about_a_pair_carries_only
  _the_pair_the_verdict_and_a_reason`. Revising a delivered requirement is a
  superseding issue, not an edit in place. `kills-only` and `tagged-single` leave
  the response schema alone and avoid all of that; `tagged-single` is
  disqualified on recall, which leaves `kills-only` as the fallback if the
  schema change is unwanted.
- **The bar is not doing the work the recommendation rests on.** DR-314's rule is
  a worst-seed threshold, and on nine draws the shipped shape fails its own bar
  3 times. The recommendation is a like-for-like comparison against the
  incumbent at equal draw counts, not a threshold test.
- **Batching is still untested.** Every case fitted one call, as in DR-314.

### Three draws decided nothing, and nearly decided it wrongly

**On three seeds `kills-only` averaged 0.9688 and was written up here as the one
qualifying arm. On nine it averages 0.9410 and is the worst of the four arms
drawn that many times.** Seeds 0, 1 and 2 happened to be three of its four best
draws. Nothing about the arm changed; the sample did.

`union` moved the other way over the same widening — 0.9479 on three draws,
0.9688 on nine — so the two arms swapped places. A recommendation issued after
the three-seed round would have taken the worse arm, kept a larger response, and
cited a number that does not survive contact with six more draws.

Two rules come out of this, and they cost about $0.12 and forty minutes each to
follow:

- **Draw the incumbent as often as the candidate.** The shipped `reasoned` arm
  was extended to nine seeds only because recommending its replacement while it
  held three draws and the candidate held nine is the same error pointing the
  other way. It happened to hold up; that was not knowable in advance.
- **Do not compare minima across unequal draw counts.** A minimum over nine is
  systematically lower than a minimum over three. Where `n` differs, mean, median
  and the share of draws below a fixed threshold are the figures that survive.

DR-314 already said one draw decides nothing, and the three-seed design came from
that. This round says three is not obviously enough either, at least when the
arms differ by one or two labelled edges out of 32.
