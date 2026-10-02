# Experiment: TypeSafe Jev for pipeline judgements

*Design for testing whether Jev (TypeSafe AI's System One model) can take over fixed-label judgements in the checker: dedup verdicts, test/obligation pairing, discrimination judgements, and the small classifiers. Companion to the spec and the Stage 1 plan. Date: 2026-09-16, revised 2026-09-17 (added §3.6 calibration loop and the Mini arm; access obtained). Status: proposed.*

---

## 1. What Jev is

A hosted-only decision API (no weights, no self-host; early access via console.typesafe.ai, obtained 2026-09-17). One endpoint, `POST /v1/systemone`, takes a `state` (string, object, or array, budget about 32k tokens) plus a map of typed questions, and returns probabilities rather than text.

Three primitives. Noul: a yes/no probability. Choice: a distribution over up to 255 options plus a confidence score derived from how concentrated the distribution is. Score: a probability-weighted position across ordered levels. Each question carries `instructions` and per-option `criteria` descriptions (strings or objects with fields like what / not_for / examples). Multiple questions in one request share the state and evaluate in parallel. There is no fine-tuning; customization is entirely in the instructions and criteria text.

It cannot generate text, name a defect, explain a verdict, or reason over steps. Pricing at launch is $0.042 per million input tokens with output free; latency 70 to 500ms.

Two things to hold onto. The calibration claim (trained with "RLCD" for calibrated probabilities) is a vendor claim with no published calibration metrics on independent ground truth. TypeSafe's own workflow benchmark puts Jev at 67.8% aggregate vs 74.1% for the top LLM comparator, scored against model-derived reference labels, not verified truth. So this experiment tests calibration directly rather than assuming it.

## 2. Which judgements are candidates

The pipeline's judgements split into fixed-label outputs and text outputs. Jev can only do the first kind. Candidates, with the primitive and the ground truth available:

| Judgement | Milestone | Primitive | Ground truth on hand |
|---|---|---|---|
| Dedup pairwise verdict | dedup | Choice over equivalent / A subsumes B / B subsumes A / overlaps / distinct (or three Nouls, §3.6) | Gate 1 correction files; archetype decompositions; over-specified fixtures |
| Test to obligation mapping | M4.2 | Noul per (test, obligation) pair, or Choice over obligation IDs + none per test | SWE-bench Verified FAIL_TO_PASS vs PASS_TO_PASS; archetype labels; Gate 2 corrections |
| Discrimination given a named defect | M5.2 | Noul: would this test fail under this defect? | BugsInPy mutant kill/survive; M-B3 labels (executed, not model-derived) |
| Weak-evidence anti-patterns (§9.4) | M5.4 | One Noul each: circular expected value, assert-not-none, incomplete error assertion, critical behavior mocked, requirement not exercised, unvalidated snapshot | Archetypes #3 to #6; §9.4 examples |
| Obligation type | M1.2 | Choice over the nine types | Gate 1 corrections |
| Explicit vs inferred | M1.3 | Noul | Gate 1 corrections |
| Implementation coverage class | M3.1 | Choice over Addressed / Partial / Not / Unclear / Non-code | Gate 2 corrections; archetypes #1, #2, #8 |

Not candidates: naming the plausible defect, the explanation attached to every finding, recommendations, the next instruction, open-question generation. The LLM keeps those.

## 3. Design

### 3.1 Arms

For each task, four arms over the same labeled cases:

A. Current LLM judge (baseline).
B. Jev alone, taking argmax.
C. Hybrid: Jev decides when confidence (Choice/Score) or |p - 0.5| (Noul) exceeds the threshold for that action; otherwise the LLM decides. Thresholds are per action, not one global τ (§3.6).
D. GPT-5.4 Mini with logprobs over the option set, run through the same hybrid gate. This is the bar Jev has to clear: it needs no new vendor dependency and is available now. Run it first.

Every arm reports accuracy against labels, cost per case, latency per case, and for the hybrid arms the fraction auto-decided.

### 3.2 Measurements

Accuracy against ground truth, with per-class precision and recall. Name the costly error per task: overmerge for dedup (a false "equivalent"), a false "discriminates" for M5.2, a false "Addressed" for M3.1. Report precision on that class separately.

Calibration: reliability diagram, Brier score, ECE. This is the measurement that decides whether the gate is usable. If accuracy is flat across confidence bins, confidence carries no information and the hybrid collapses to argmax.

Self-consistency: repeat each query five times and count verdict changes. For dedup, submit both orderings (A,B) and (B,A) in one request and count asymmetric verdicts; this is the existing symmetry noise signal, obtained for free.

Transitivity (dedup only): run the existing blocking and complete-linkage clustering on Jev verdicts and count triangle violations, compared against the LLM judge on the same pairs.

Consistency with the LLM: agreement rate, and inspection of disagreements. Where a label exists, disagreement tells you which judge is wrong; where it doesn't, a disagreement is a candidate for hand labeling.

### 3.3 Prompt construction

State is a structured object, not prose. Dedup: `{task_context, obligation_a, obligation_b}` with obligations as their raw text plus type. Mapping: `{obligation, test_source, implementation_hunk}`. Discrimination: `{obligation, test_source, implementation_hunk, named_defect}`. Keep the implementation hunk bounded (M2.2's retrieval budget) so the 32k budget holds.

Criteria descriptions use the violation-set definitions already written for the dedup labels, since those were designed to work on raw obligation text. Use the object form (what / not_for / examples) for the confusable pairs: equivalent vs subsumes, overlaps vs distinct.

Record every request and response through the M0.4 harness so runs replay without live calls and results are reproducible.

### 3.4 Sizes

Minimum for calibration to mean anything is a few hundred cases per task with both classes represented. Dedup pairs are easy to generate: blocking produces candidates, and the negatives are free. For discrimination, take as many BugsInPy mutants as M-B3 has produced with a mapped test; if fewer than 200, extend with SWE-bench PASS_TO_PASS mutants. For mapping, a stratified 100 of SWE-bench Verified gives several hundred (test, obligation) pairs after decomposition.

### 3.5 Order

1. Discrimination vs mutants first. It is the only task with executed ground truth, so it answers the calibration question without a model-derived label in the loop. If Jev's confidence doesn't track kill/survive here, the rest matters less.
2. Dedup second. Cheapest to run (every pair fits, both orderings per request), and it is the task that motivated this.
3. Anti-pattern Nouls and the small classifiers third. Low effort, run in the same harness.
4. Mapping last. The 32k budget and the need for implementation context make it the fiddliest, and its SWE-bench labels are coarser than the others.

### 3.6 Calibration loop (tune our side before judging the model)

"Calibration" means two things here and the experiment needs both. §3.2 measures whether Jev's probabilities are honest. This section is the other half: tuning the setup to our data. With no fine-tuning, the criteria text, the question decomposition, and the thresholds are the only levers, and an untuned Jev against a tuned LLM prompt is not a fair comparison.

Split first. Before touching anything, split the labeled cases per task into a dev set and a holdout (roughly 60/40, stratified by class). All tuning below happens on dev. Only holdout numbers are reported, and the holdout is scored once per arm at the end. The Mini arm gets the same dev-set iteration so neither side has the tuned-vs-untuned advantage.

Criteria iteration. Run dev, look at the confusion matrix, and rewrite the criteria for the confused pairs using the object form: `what`, `not_for`, and two or three `examples` drawn from dev cases (never from holdout). For dedup, expect trouble on equivalent vs subsumes and overlaps vs distinct. Stop when a rewrite stops moving dev accuracy; record each version in the harness so the sequence is inspectable.

Decomposition. Where one Choice carries a compound judgement, try atomic Nouls combined in code. For dedup, compare the five-way Choice against three Nouls: A's violations are a subset of B's; B's violations are a subset of A's; A and B share at least one violation. Equivalent, subsumes in either direction, overlaps, and distinct all fall out of the three answers deterministically, symmetry is by construction, and each Noul's probability can be thresholded separately. Report both forms on holdout.

Per-action thresholds. One global τ is wrong because the errors cost different amounts. Set a threshold per action, on dev, by picking the confidence at which the auto-decided slice reaches the target precision for that action's costly error. Auto-merge on "equivalent" needs the strictest threshold (overmerge is not recoverable downstream); auto-decide "distinct" can be looser; "discriminates" in M5.2 sits near the strict end because a false "this test catches the defect" is exactly the false green the product exists to prevent. Everything below its threshold escalates to the LLM.

Post-hoc recalibration. Fit Platt (logistic) or isotonic scaling on dev to Jev's raw probabilities, then check on holdout whether ECE and the reliability diagram improve. Do the same for Mini's logprobs. Two findings matter: whether Jev's raw probabilities are usable without recalibration (the vendor's claim), and whether Mini's logprobs become competitive after recalibration (which would weaken the case for Jev). Report raw and recalibrated numbers side by side.

What this changes in §4: the adoption bar is evaluated on holdout, with per-action thresholds, after the dev-set loop has run for both Jev and Mini. If Jev only clears the bar after post-hoc recalibration, adopt with the recalibration step built into the harness and note that the raw probabilities were not sufficient.

## 4. Adoption bar

Adopt Jev for a task when, on holdout with per-action thresholds, arm C is within two points of arm A on accuracy, auto-decides at least half the cases, has equal or better precision on the costly error class in the auto-decided slice, and beats arm D (Mini) on at least one of cost, auto-decided fraction, or calibration without losing on accuracy. Additionally, ECE must be low enough that the reliability diagram is monotone; otherwise the threshold is arbitrary.

Reject when confidence does not predict accuracy, when self-consistency is worse than the LLM's, when transitivity violations after clustering increase, or when Mini matches it on every axis (no reason to take on the dependency).

Where adopted, the finding's evidence tier is unchanged (still static), and the explanation is still produced by the LLM for the cases it handles; for Jev-decided cases the finding records "fast-screen verdict, no rationale" so the user can see which judgements have no linked reasoning. This keeps the §2.5 commitment honest.

## 5. Risks and constraints

Data leaves the network on every call to a single US-hosted vendor with no on-prem option. Acceptable for the personal build; a real constraint on the commercial goal, since customers would be sending source and tests to a third party. Decide this before building a hard dependency.

Early access: rate limits, p95 latency, and reliability are unpublished. Launch pricing may not be sustainable.

No explanation means findings decided by Jev break the "every conclusion links to evidence and rationale" property unless the LLM backfills. Budget for that if adoption goes ahead.

The vendor's own benchmark shows a measurable accuracy gap vs frontier LLMs, and roughly parity with the small-model tier. Expect Jev at or below Mini on accuracy, with the gap widest on the discrimination judgement (needs code reasoning Jev cannot do) and narrowest on dedup (short text). The hybrid arm exists because Jev alone is expected to lose on accuracy; the bet is that its confidence is more honest than Mini's logprobs, so the confident subset is good enough.

Local open-weight models are not an arm for now: zero-shot at 4B to 12B they will lose to Mini, and the two reasons to revisit (a customer requiring on-prem, or enough labels to fine-tune a cross-encoder for dedup) are not live yet.

## 6. Open items

Confirm rate limits before sizing runs. Confirm whether the current dedup labels are stored in a form the harness can read directly (the M-B6 correction shape). Decide whether to include task context in the dedup state or judge pairs in isolation; run both if cheap. Confirm GPT-5.4 Mini exposes logprobs on constrained single-token output in the mode used.

Sources: TypeSafe blog (Introducing System One Models and Jev), docs.typesafe.ai (API reference, System One concepts, Choice primitive), Kingy AI review, Modem Guides reality check, Anthony Maio (Jev: The Language Model That Won't Talk), Valyu AI practical guide on dev.to.
