# #191 — the pre-change instability baseline

The measurement #191's Acceptance is scored against: *"Step 1's harness (#189) is
re-run and reports lower resample variance and lower perturbation sensitivity
than the pre-change baseline, per model."*

Taken before any change to `evidence/discrimination.py`, because taking it after
is not recoverable — the request key moves, the recorded discrimination
transcripts orphan, and the pre-change judgement can only be re-obtained by
checking out the old code and paying for the calls again.

## How to reproduce it

```bash
.venv/bin/python docs/experiments/191-discrimination-partition/retake_baseline.py
```

Replay-first, and that is not a convenience: the original recordings are in
`.acceptance/cache/transcripts/`, so a correct reconstruction of the case
replays end to end and costs nothing, while a key miss means the reconstruction
is wrong rather than that a live call is owed. `--record` allows live calls.

The script needs a clone of this repo checked out at the case's head revision;
it reads `inputs.repo` from a path it does not create. See `case-repo` in the
script.

## The case

| | |
|---|---|
| case | `167-gate2-run4` — the corpus's strongest positive anchor (`tests/fixtures/rating-regression/167-gate2-run4/case.json`) |
| task text | `tests/fixtures/rating-stability/167-gate2-run4/current-task.md`, digest `d9095f91e5f987c8` |
| revisions | base `839ea47`, head `52c52b8` |
| model | `openai/gpt-5.4-mini` |
| runs | 3, seeds 1000 / 1001 / 1002 |
| perturbation | `add-unrelated-test` |

The digest is asserted by the script. It is the check that the reconstruction is
the same case and not merely a similar one.

## What it says

**Discrimination is one call.** Over 19 obligations with mapped evidence, in the
same run where decomposition took 3 calls and mapping took 7:

```
_Decomposition: 3   _Mappings: 7   _Discrimination: 1   _Coverage: 1
```

**The answer is uniform to a degree the input does not explain.** Every one of
the 19 obligations came back with exactly 2 defects, and all 38 verdicts were
`would_be_caught: true`. Three runs, same shape each time. That is the DR-164
signature — a schema-constrained call staying schema-valid while shedding the
work — rather than a set of 19 independent judgements.

**The defect set does not repeat at all.** 114 distinct
`(obligation, defect wording)` keys across the three runs, each appearing
**exactly once**: no defect was worded the same way twice over identical input.
This is DR-180's second-order finding, measured.

**So the verdict axis currently cannot register a flip.** `compare_runs` keys a
verdict on the exact defect string. With no key shared between two runs there is
nothing to compare, and the axis reports zero differences *by construction*.
Verdict stability here is unmeasurable, not good — and a post-change run that
reports *more* comparable subjects, or more detected differences, is the axis
starting to work rather than a regression. Read the count of comparable subjects
before reading the count of differences.

| figure | pre-change |
|---|---|
| defects per run | 38 (19 obligations × 2) |
| `would_be_caught: true` | 38 of 38, every run |
| defect keys shared by ≥2 runs | **0 of 114** |
| evidence-class content differences across runs | mean 0.67, spread 2.0 |
| perturbation `add-unrelated-test` | 1 of 21 watched judgements moved (one `evidence_class`) |

## A caveat on the perturbation figure

`_perturbation_result` counts obligations and open questions in
`watched_judgements`, but counts *any* content difference in
`changed_judgements` — including a defect-verdict flip, whose subject is not in
the denominator. The two were consistent only while the verdict axis was empty.
Queued in `docs/DEFERRED.md`.

## The post-change measurement

`post-change-instability.json`, same case, same model, same three seeds, same
perturbation. Every request changed, so nothing replayed and this one was bought.

**#191's Acceptance asks for lower resample variance and lower perturbation
sensitivity. It got neither.**

| axis | pre | post |
|---|---|---|
| `evidence_class` differences across the three run pairs | **2** | **16** |
| perturbation, `evidence_class` only | 1 of 21 | **5 of 21** |
| perturbation, all kinds | 1 of 21 | 13 of 21 |
| defect wordings shared by ≥2 resample runs | 0 of 114 | **0 of 141** |

The `evidence_class` row is the honest comparison: that axis was measurable
before and after, and it is eight times worse. Read the other rows with the
caveats below before drawing anything from them.

### What did NOT happen: enumeration did not become deterministic

141 subjects over 141 observations — every defect wording still appears exactly
once across the three runs, exactly as before.

This is not a bug, and it is worth being precise about what the change actually
promises. The three resample runs use **different seeds**, and the seed is in
the request key, so each is a genuinely independent draw. #191 makes an
obligation's enumeration invariant to *test edits* — same request bytes, so the
transcript replays. It does nothing to make the model's enumeration reproducible
across independent samples, and nothing in the mandate asks it to. Constraint-12
("two runs over the same obligations and the same changed code enumerate the
same defects") holds in the replay sense and fails in the resample sense, and
the tests assert the replay sense.

### What DID happen: the verdict axis became measurable, and it is bad

The perturbation run shares seed 1000 with baseline run 0 and differs only by an
added test file. Test files are filtered out of the enumeration request, so that
request is byte-identical and replays — which is the mechanism (b) exists for.
The consequence shows up in the numbers:

**8 verdict flips on defects whose wording is identical**, e.g.

```
`acceptance recommendation --criterion <id>` returns that criterion's
recommendation from stored review state
    would_be_caught  True -> False
```

Pre-change this was structurally impossible to observe: the single combined call
carried the tests, so an added test changed the request, changed the wordings,
and left no shared key to compare. The baseline's `1 of 21` was not a low number,
it was an unmeasured one.

So the perturbation row is not comparable pre-to-post. 8 of the 13 changed
judgements are verdict flips that pre-change could not be counted, and they are
not in the denominator either — see the ratio defect queued in `DEFERRED.md`.
The comparable part is 1 → 5 on `evidence_class`.

### The regression that is real

Eight times more `evidence_class` movement across resamples is not an artefact
of better instrumentation. `evidence_class` was fully measurable before.

The likely mechanism is the change itself. `defect_verdict_batch_size` defaults
to 1, so a review that made **one** verdict judgement call now makes one per
criterion — nineteen independent draws where there was a single sample. Removing
work-shedding and adding sampling variance are both real effects of partitioning,
and on this case the second dominated. That is a hypothesis this measurement
does not settle: it was taken at one batch size, and a run at a larger verdict
batch would separate the two.

**Recorded as a negative result rather than tuned away.** DR-180's governing
constraint cuts both directions — stability must not be bought by blunting the
judge, and a batch size must not be picked to make this table look better.

## Third measurement: the code restored to the verdict call

`post-fix-instability.json`. Same case, model, seeds and perturbation.

| | pre-change | split, no code in verdict | code restored |
|---|---|---|---|
| `evidence_class` diffs across the three run pairs | 2 | 16 | **13** |
| perturbation, all kinds | 1 of 21 | 13 of 21 | 12 of 21 |
| perturbation, `evidence_class` only | 1 | 5 | 6 |
| defect verdicts, `caught` / `not caught` | **114 / 0** | 111 / 30 | **82 / 52** |
| defects per criterion, range over 3 runs | 2–6 | 2–10 | 1–11 |
| #190 rating-regression suite | 34 pass | 34 pass | 34 pass |

### Restoring the code did not recover the variance

16 → 13 against a baseline of 2. The information-starvation hypothesis explains
about a fifth of the regression and is not the main cause. It was still the
right fix — removing that input was never asked for and made the judge worse on
its own terms — but it does not explain the number.

### The baseline was stable because it was degenerate

This is the result that matters, and it inverts how the whole comparison should
be read.

**The pre-change judge answered `would_be_caught: true` to 114 of 114 defects,
across all three runs. It never once said a test would fail to catch anything.**
Combined with what the first baseline already showed — exactly two defects per
criterion, every criterion, every run — that is not a judge with low variance.
It is a constant function, and a constant function is perfectly stable.

Restoring the code roughly doubled the rate at which the stage says *not
caught*, from 21% to 39%, and widened defects-per-criterion from a near-fixed
2–6 to 1–11. A discrimination stage that never returns "not caught" cannot find
a weak test, which is the only thing it exists to do.

So `lower variance than the pre-change baseline` is not a criterion this change
should be trying to satisfy. Satisfying it means returning to the rubber stamp.
DR-180's constraint — *stability must not be bought by blunting the judge* —
turns out to describe the **baseline**, not the change.

### What this does not establish

That the new verdicts are *right*. Variance and correctness are different axes,
and a higher "not caught" rate is equally consistent with a judge that has
started over-flagging. #190's suite still passes 34 of 34 in all three
conditions, which is the only correctness evidence here, and it is a small suite
built before any of this. A discrimination-rate floor measured against labelled
cases is what would settle it.

The remaining variance is real and unexplained. Three candidates survive:
nineteen independent samples where there was one, the loss of cross-criterion
anchoring within a single response, and unstable mapping upstream feeding the
verdict different evidence each run — which the perturbation analysis already
showed is happening.

## Provenance of the file itself

`baseline-instability.json` was produced by the run above and is byte-identical
to the first attempt at this baseline everywhere except the defect-verdict axis,
which went from 0 subjects to 114 once the harness read the responses instead of
a type that never crosses the client. The judgements are the same recordings;
only the extraction changed.
