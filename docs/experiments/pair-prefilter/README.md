# Prefilter the pair set — experiment notes

Working notes for offline experiments on whether a cheap filter can cut the
(defect, test) pair set before the judge in `defects/pair_mapping.py` sees it.
Written in the shape of `docs/experiments/obligation-dedup/README.md`, so the
next experiment starts from the method rather than rebuilding it.

**This file is the method and its traps. The findings are `FINDINGS.md`, and
the raw numbers are `findings.json`.**

## Why the question exists

#314's Gate 2 run judged **12,450 pairs and recorded 127 kills — a 1.0% kill
rate** — costing **$3.51 of that run's $4.25**, of which **$2.46 was output
tokens**. Neither of the usual levers reaches that. Prompt caching discounts
input only. Batching cannot lower the call count, which is floored by the
judgements-per-request limit: 12,450 judgements at 40 per request floors at 312
calls and the run issued 332.

**A prefilter is the only lever that reaches output**, because removing a pair
removes its verdict. At a 1.0% kill rate, 99% of what is paid for comes back
*survives*.

#314's shipped prefilter, `defects/reachability.py`, is a soundness filter: it
excludes only when a path is *provably* absent, and therefore excludes almost
nothing. That was the right call for that issue and is not what this measures.
This asks whether an *unsound* filter — one that can be wrong — is wrong rarely
enough to use.

## What is here

- `corpus.py` — reassembles the run into the inputs a prefilter would see. Run
  it directly for a survey. **Every experiment on this data should start with
  that.**
- `locality.py` — the free baseline filter: does the test's discovery signal
  touch the defect's own file?
- `embeddings.py` — recorded Voyage calls, with the free-tier rate limit paced.
- `score.py` — the scoring sweep; writes `findings.json`.
- `score-output.log` — the run that produced the findings, kept as its evidence.
- `verdicts.json.gz` — the 12,450 recorded verdicts, committed. The only part
  of the run that cannot be re-derived without paying for it again.

## Running it

`discover_tests` reads a working tree rather than git blobs, so the tests have
to be read at the reviewed head:

```bash
git worktree add --detach ../314-prefilter-head 2945551
.venv/bin/python docs/experiments/pair-prefilter/corpus.py \
    --worktree ../314-prefilter-head          # the survey, no network

set -a; . ./.env; set +a                       # only the embedding filters need a key
.venv/bin/python -u docs/experiments/pair-prefilter/score.py \
    --worktree ../314-prefilter-head
```

`--no-embeddings` runs the free baseline alone and makes no call at all.

Embeddings are cached under `.acceptance/cache/`, so a second run is free. The
first costs a few cents and about twelve minutes — **the twelve minutes are the
rate limit, not the work**. An account with no payment method on file is held to
3 requests and 10,000 tokens per minute, which Voyage states in the body of the
429 it returns.

## What is measured, and against what

For every candidate, one question: **at a threshold that excludes X% of pairs,
how many of the 127 recorded kills does it exclude?**

A filter that loses a kill at any useful threshold is rejected. The failure
modes are not symmetric, which is the whole reason the bar is set there. A wrong
exclusion silently un-covers a defect and re-creates the failure #312 exists to
remove — a recommendation prescribing a test that already exists (#250, #287).
A filter that excludes too little only costs money.

Four candidates, per the queued plan:

1. **The free baseline, measured first.** Does the test's discovery signal touch
   the defect's own file? No embeddings. If this excludes a large share with no
   kill loss, the embeddings are unnecessary; if not, it is the bar they must
   clear.
2. **Defect description against test source** — cross-modal.
3. **Implicated code region against test source** — code to code.
4. **The union of those**, per the standing instruction of 2026-08-30: run
   several filters and reject a pair only when **all** of them reject it, and do
   not weigh embedding cost, which is negligible next to a model call.

## Traps

**1. The 127 kills are the judge's own answers, not ground truth.** This
measures agreement with ourselves. For a prefilter that is the right target —
its only job is to avoid skipping a pair the judge would have called a kill —
but it is not evidence that the judge is right, and no write-up may imply it is.

**2. One review.** Every number here comes from a single Gate 2 run over this
repo's own code. Any threshold tuned on it needs holding out against #315's
archetype labels before being trusted, exactly as DR-259 held out a fifth task
file — and DR-259's held-out check is the reason to expect that to hurt.

**3. Node ids must match, and `corpus.py` refuses to proceed if they do not.**
The verdicts name tests by pytest node id, and the tests are re-derived by
running `discover_tests` at the head revision. An id the verdicts do not carry
makes that test's pairs silently vanish from every score, and each filter then
looks better than it is. `load()` compares the two sets and stops.

**4. The free baseline is not `reachability.py`, and must never be described as
if it were.** That module proves absence and is sound. This one asks a one-hop
name question and is not: a test calling a helper that calls the defect's code
references no changed name and would still fail. `reachability.py`'s docstring
sets out that case; the measurement here says how often it actually happens.

**5. The code-region filter uses evidence the judge never saw.** `pair_mapping.py`
shows the model the defect's id, type and `description`, and the test's own
source — and nothing else. It is never shown the implicated hunks. A filter over
those hunks is therefore predicting the judge's answer from material the judge
did not have, which is allowed for a prefilter but changes what "agreement"
means for that one candidate. The description filter has no such gap: both sides
of it are exactly what the judge was given.

**6. Pin what is embedded.** `score.py`'s `DEFECT_TEXT`, `TEST_TEXT` and
`REGION_TEXT` name it exactly. Changing what goes in moves every distance and
invalidates any threshold read off this run, without changing the threshold.
This is DR-259's trap 7, which cost that analysis real time.

**7. Regions are embedded once each and scored by best match**, not concatenated
per defect. One defect here implicates eleven hunks and concatenation would
average its signal away. It is also 18,000 tokens instead of 291,000, because 75
defects name only 23 distinct regions between them.

**8. `input_type` is real and the product cannot send it.** Voyage's endpoint
accepts `query` or `document` and rejects a third value with a 400 naming those
two — verified against the live API on 2026-08-30. `ModelClient.embed` sends
`model` and `input` only, so adopting an asymmetric filter means changing
`build_embedding_request`, **which moves the embedding request key and orphans
the recorded linking transcripts**. `score.py` measures the symmetric form
alongside the asymmetric one so that cost is only paid if it buys something.

**9. DR-259 is a caution, not a precedent.** Its held-out check found no
threshold that separated cleanly. But it answered a different and harder
question — whether two obligations state the same requirement, a
semantic-equivalence judgement — where this asks the much cruder "is this test
even about this code". The difficulty does not transfer directly. Read DR-259's
*Held-out check* section before assuming either way.
