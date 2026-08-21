# Decision Record 173 — Mapping twin-splitting: what was measured, and what is ruled out

*Relates to issue #173 (closed 2026-08-21, under umbrella #182). Status:
**findings recorded; issue closed as too narrowly scoped; superseded by a larger
change the human is filing separately.** Track: checker. Stage: 1.*

*A findings record, not a resolved decision, in the shape of `DR-180`. It exists
because four measurement rounds and roughly $14 of model calls produced mostly
**negative** results, and a negative result that is not written down is
indistinguishable from an untried idea. Two of the hypotheses refuted here are
plausible enough that they will be proposed again.*

---

## What #173 claimed, and why it was closed

#173 was filed as a **precision** defect: the mapping stage declines the
on-point obligation↔test pairing and accepts looser ones. Four instances were
recorded on the issue between 2026-08-03 and 2026-08-20, the sharpest being
#216's and #293's, where the tool **prescribed a test that already existed in
the diff** and that it had itself mapped to neighbouring obligations. That shape
makes a gate unreachable by iteration: no honest change satisfies the finding.

Measurement did not support the framing. The stage is not systematically blind
to on-point pairings; it is inconsistent about demands that are stated more than
once, and separately it is noisy from call to call. Neither is fixable by the
narrow change #173 implied, so the issue was closed in favour of a larger one.

## 1. The recorded failure is one draw from a distribution

Re-issuing the byte-identical recorded request from #293's instance
(transcript `c3f75a2e067e…`) against the same model, temperature and seed:

| measurement | result |
|---|---|
| on-point pairing returned | **20 of 25 draws (80%)** |
| distinct full answers | **23 across 25 draws** |
| mean pairwise edge agreement (Jaccard, test→obligation edges) | **0.73** |
| the test #173 was filed about — distinct id-sets | **10 variants, modal 12/25** |

The recorded failure reproduces 1 draw in 5 with the identical four ids. The
stage was right about that pairing four times in five; the pipeline takes one
draw and stores it as a finding.

Confounds checked rather than assumed: `mark_reusable_opening` is a no-op for
`openai/gpt-5.4-mini`, so the re-issued request is byte-identical to the
recording; and `_litellm_effective_controls` confirms `temperature=0.0` and
`seed=0` both reach the provider rather than being silently dropped. The
variance is the provider's own.

> **The methodology consequence outlives this issue.** A single run cannot
> evaluate any change to the mapping stage. Every mapping prompt change made in
> this repo before 2026-08-21 was assessed on evidence that could not support the
> assessment, in either direction. #173's own 2026-08-03 comment — *"did not
> reproduce on the next run"* — was read as the defect being elusive; it is what
> an 80% process looks like sampled twice.

## 2. Twin-splitting is real, systematic, and measurable without labels

Where two obligations of one request state the **same demand**, a test that
evidences it is mapped to only one of them roughly half the time.

| corpus | distinct decompositions | shared | split | rate |
|---|---|---|---|---|
| recorded transcripts, hand-confirmed twins | 4 | 14 | 18 | **56%** |
| committed `dogfood-logs/` reports, sim ≥ 0.55 | **76** | 200 | 228 | **53%** |

Two corpora, two parsers, the same answer.

This matters beyond the number, because **it needs no hand-labelled ground
truth**: two obligations stating the same demand must receive the same answer,
so "mapped to exactly one" is an objective error. It is the only mapping-quality
figure that can be recomputed over committed data at any time with no model
calls, and it is preserved as `acceptance.benchmark.twin_splitting`.

It also explains #173's headline symptom mechanically: pick the twin, and the
on-point obligation reports *no mapped test* while the recommendation stage
prescribes a test that already exists and is cited elsewhere in the same report.

**The decomposer already detects the collision.** Ids of the form `<base>` and
`<base>-2` mean it generated the same slug twice, noticed, and disambiguated
instead of merging — see #304. The information needed to merge is present at
decomposition time and discarded.

### The confound that must travel with the figure

Split rate rises as pairs get *less* identical — 45% at similarity 0.80–0.89,
60% at 0.60–0.64. **This is not an error curve.** Below identity, mapping a test
to only one of two obligations is frequently the correct answer, so a mapper
with no defect would also produce a rising line. Only **byte-identical** text
makes a split unambiguously wrong, and there the sample is thin: 3 of 16
opportunities. `twin_splitting.by_band()` reports bands separately and never
totals them for this reason.

## 3. What is ruled out — do not re-derive these

### The obligation's id does not drive the judgement

#173's standing hypothesis was that the id `adding-test-to-**unmapped**-file-…`
asserts the opposite of its own description, and that ids carry weight. Correcting
the id gave 5/5 against a control already at 4/5 — no detectable effect, and the
control shows the premise (a systematic rejection) was wrong to begin with.

### Prompt wording is a well-powered null

Four arms over 46 real corpus requests, 8 draws each — **1,472 calls**.

| arm | split rate | vs control | correct (shared) |
|---|---|---|---|
| control | 148/748 = 19.8% | — | 600 |
| remove the *"five or more ids"* sentence | 149/726 = 20.5% | z=−0.35, **p=0.72** | 577 |
| add explicit "restatements must both be returned" | 111/690 = 16.1% | z=1.82, **p=0.068** | 579 |
| both changes | 123/633 = 19.4% | z=0.17, p=0.87 | 510 |

The mapping prompt genuinely does contain two instructions in tension — *"return
every id that passes… do not choose between overlapping obligations"* against
*"a test returning five or more ids is usually a test whose ids were not each put
to THE TEST"* — and against this repo's convention of stating every rule twice,
the honest id count is structurally high. It is a good story. **Removing the
second instruction changes nothing.** Expect it to be proposed again.

The explicit twin rule is the only arm that moves, weakly: 3.7 points, p=0.068,
under a fifth of the errors. Combining both changes loses that gain and costs 90
correct mappings.

### The forced per-obligation verdict cuts splits by destroying recall

The natural conclusion from the above is that the defect is structural, not
verbal: `test → [obligation_ids]` lets every obligation compete for a slot in one
shortlist, and no prose can force per-obligation evaluation when the output shape
rewards picking a list. The corresponding fix — a verdict required for **every**
obligation, `test → {obligation_id: bool}`, enforced by `strict` mode so a
shortlist is impossible — was piloted over 6 requests × 6 draws:

| arm | split | shared | mean ids/test | tests answered | cost/call |
|---|---|---|---|---|---|
| control | 19/172 = 11% | 153 | 1.54 | 9.2 | $0.00423 |
| verdicts | 1/63 = **2%** | **62** | 0.57 | 9.2 | $0.00981 |

**The split rate improved for the wrong reason.** Both arms answered the same
number of tests, so nothing was skipped — the verdict arm answered *false* far
more often, losing **91 of 153 correct twin-mappings, a 59% recall loss**, to
remove 18 splits. Asked in isolation whether a test would fail if one
obligation's behavior were missing, the model defaults to no. That is DR-164's
shedding failure, which #164 exists to prevent.

> **The decision that is settled here:** a split-rate-only measurement would have
> scored this variant a success. Any successor must be scored on **recall as well
> as splits**, and rejected if `shared` falls below control. The guard metric
> (mean ids per test, 1.54 → 0.57) is what caught it.

## 4. Prompt caching — measured here because it bounds what any fix may cost

Recorded per-call usage over repeated mapping calls sharing a prefix, run
sequentially so the cache could warm:

Warming curve: 48% → 73% → **94% → 94% → 94%** → 83% of prompt tokens served
from cache. Warm cost **$0.00423/call** against **$0.0089** for the recorded
pre-#265 transcript at 0% cached — roughly **half**.

Two consequences:

- **The ordering principle was already validated, on another stage.** #191's
  branch measured **84–93%** of each *discrimination* verdict request served
  from the provider's cache, live, because both its prompts put the invariant
  code block first and the per-batch criteria last (`session-state/191.md`,
  2026-08-13). #265 generalised that ordering to every stage. So the open
  question is not whether prefix ordering buys reuse — it does — but whether
  #265 extended it to mapping in a live run.

  Every recorded transcript in the corpus still shows `cached_tokens: 0`, and
  they all predate #265, so **mapping in production remains unmeasured** even
  though discrimination does not. Within one review the obligations block is
  shared by every partitioned mapping call and should warm after the first.
  Cheap to confirm; worth about half the model spend of a run; belongs to #184.

  *(Recorded because the first version of this section said the benefit was
  unmeasured outright. It was not — #191 had measured it eight days earlier on
  a branch that was never merged, and the finding sat only in a session-state
  file. Work parked on an unmerged branch is invisible to whoever measures the
  same thing next.)*
- **The discount is input-only.** The failed verdict arm's penalty was 2.5×
  *output* (787 → 1,981 completion tokens/call), which is never cached, so its
  cost stayed 2.3× control even at a 74% hit rate and does not amortize as the
  cache warms. **No design that grows the response can be paid for by caching.**

## 5. What is preserved, and where

- `src/acceptance/benchmark/twin_splitting.py` — the label-free measurement, over
  committed `dogfood-logs/` reports, no model calls. `tests/benchmark/test_twin_splitting.py`
  asserts the shape of the result rather than a fixed rate, so new dogfood runs
  do not fail it.
- `docs/DEFERRED.md` — the drafted filings this work produced, including the
  #304 evidence and the caching finding, neither of which closed with #173.
- The transcript corpus (`.acceptance/cache/transcripts/`, gitignored) was
  **orphaned by #265** and replays against nothing, but every recording remains
  readable as a *request* and that is how all of the above was measured. An
  orphaned transcript is not a lost one.

## What this does not settle

No fix. Four rounds ruled things out and none ruled anything in. The one design
left standing and untested is a **recall-preserving second pass**: keep the
list-shaped call unchanged, then show the model the obligations it did *not* map
for each test and union any it accepts. It is monotone — the first pass is
untouched, so correct mappings cannot be lost, only added — and the twin that
lost a coin flip is exactly an item in the omitted set. Its risk is the opposite
failure, over-mapping, which the same guard metric already measures.
