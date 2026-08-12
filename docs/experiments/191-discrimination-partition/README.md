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

## Provenance of the file itself

`baseline-instability.json` was produced by the run above and is byte-identical
to the first attempt at this baseline everywhere except the defect-verdict axis,
which went from 0 subjects to 114 once the harness read the responses instead of
a type that never crosses the client. The judgements are the same recordings;
only the extraction changed.
