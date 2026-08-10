# Judgement — #232/#219/#230 bundle, Gate 2, run 2

Base `eb182de`, head `dbbc47d`. **Not clean.** 15 obligations, all *addressed*;
14 of 15 have mapped test evidence; **6 rated below strongly supported**, and no
open questions.

## What the change achieved, measured on this repo's own task file

| | before | after |
|---|---|---|
| scope exclusions inverted into obligations to do the excluded work | 4 of 6 | **0 of 6** |
| Completion expectations keeping their test demand | 0 of 5 (run 1), 2 of 5 (run 4) | **5 of 5, typed `test_demand`** |
| Constraints given invented test framing | 3 of 8 (run 7) | **0 of 8** |
| behaviour ↔ test-of-behaviour merges | 3 | **0** |

All six exclusions decline with reasons that name what is out of scope and
assert nothing about the change.

## Why the gate is not clean: rating instability, not a gap in the work

Between Gate 2 run 1 and run 2 the only change was **two added tests** in
`tests/prompts/test_decomposition_prompt.py`, addressing run 1's single finding.
That finding did improve — `test-sibling-scope-exclusions-same-disposition`
went *unsupported* → *partially supported*. Five unrelated obligations got
worse:

| obligation | run 1 | run 2 |
|---|---|---|
| `test-byte-identical-review-state` | strongly supported | **unsupported (no mapped test)** |
| `sibling-scope-exclusions-same-disposition` | strongly supported | partially supported |
| `no-preserve-property-reason` | strongly supported | partially supported |
| `byte-identical-review-state-on-identical-input` | strongly supported | partially supported |
| `tests-no-live-model-calls` | strongly supported | partially supported |

None of their evidence was touched. `tests-no-live-model-calls` is the clearest
case, because its mapped set did not merely change — it **grew**:

```
run 1, strongly supported          run 2, partially supported
  6 mapped tests                     8 mapped tests
  ...                                ... plus test_the_prompt_quality_test_
                                         actually_consumes_a_committed_transcript
                                     ... minus test_no_model_call_is_made_when_
                                         every_pair_is_structurally_settled
```

More evidence, weaker rating — and the test it dropped is the one added in this
change that most directly demonstrates the property (no model call is made when
every pair is structurally settled).

That is **#180** — judgement stability, which replay determinism does not cover
— compounded by mapping churn (**#182**). Attributing rather than iterating:
the gate cannot be converged on by adding tests when adding a test moves five
unrelated ratings.

## Second finding: `check` reviews its own output file

`acceptance check ... > dogfood-logs/<run>/output.log` cannot be replayed. The
shell creates the redirect target before the process starts, `check` reads the
working tree as head, so the log becomes part of the diff under review and the
coverage request key changes between the record run and the replay.

The first Gate 2 attempt failed exactly this way — `no recorded transcript for
request 9671a174…` — with a message blaming an edited prompt. This collides
directly with the dogfooding convention in CLAUDE.md, which requires `output.log`
to live inside the committed run directory. Both logs here were captured outside
the repo and copied in afterwards.

## Unrequested changes — reviewed, all four `in_service` are the work itself

The report flags the linking pair-skip, the exclusion prompt change, the
`ObligationType` docstring and the corpus manifest edit. All four are this
change; the mandate states behaviour and not mechanism, so a mechanism the
mandate does not name reading as "unrequested" is expected. The two `separable`
flags are `session-state.md` and `docs/DEFERRED.md` — correct, and they are
process files this repo commits alongside the work.

## Disposition

Presented at the gate, not worked around. The two findings are queued as
filings against #180/#182 and a new one for the output-file collision; no
finding here is attributed to an unmet requirement of the task.
