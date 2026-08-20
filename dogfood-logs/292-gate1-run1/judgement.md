# Judgement — #292 Gate 1, run 1

Run `1ee26beb851d7843`, continuing `3774fbcd223e7e5e` (#251's Gate 1 run 5).
Branch `292-rating-names-its-change` at `2fef2a6`, which is `origin/main`.

## Headline

`2 derived, 23 carried, 3 revised; 1 decompose call`. 28 requirements, 27 with
obligations, 1 deliberately given none (`completion-01`, the bare
`Implementation` marker). **Zero open questions**, so the gate's three-case
triage table has nothing to apply.

The carry worked as #269 intends: 14 requirements belonging to #293 and #291
were REMOVED with their obligations dropped, the 23 that survive the split were
carried unchanged, and only the two genuinely new scope exclusions were derived.
One model call, not five.

## Is the breakdown accurate?

**No missing obligations.** Every one of #292's eight Acceptance items has at
least one obligation, most of them two (a Constraint and its mirroring Completion
expectation):

| Acceptance item | obligations |
|---|---|
| receives stored rating + dependency changes | `changed-criterion-gets-stored-rating`, `changed-criterion-gets-dependency-changes`, `changed-criterion-gets-stored-rating-and-dependency-changes` |
| part of the recorded request | `stored-rating-and-changes-recorded-with-judgement-request`, `stored-rating-and-dependency-changes-in-request` |
| naming a given change is accepted | `changed-rating-names-one-given-change`, `changed-rating-must-name-a-change` |
| naming none is rejected, rating stands | `reject-rating-change-without-named-change-in-reader`, `rejected-judgement-keeps-stored-rating`, `changed-rating-with-no-change-is-rejected-and-rating-stands` |
| rejection by the reader, not the prompt | `reject-rating-change-without-named-change-in-reader`, `judgement-reader-performs-rejection` |
| a rejected judgement is reported | `rejected-judgement-reported` (merged across `constraint-07` and `completion-07`) |
| no stored state → no stored rating in any request | `no-stored-state-judges-all-criteria`, `no-stored-rating-in-requests` |
| `tests/fixtures/rating-stability/` findings still found | `rating-stability-fixtures-still-found` |

**No invented obligations, but one degenerate one.** All eight scope exclusions
produced correctly-negated obligations — including the two new ones, which is
what they were added for. `exclusion-01` reads *"The change does not narrow which
criteria are judged again"*, correctly keeping #293's half out.

## Finding 1 — the Task headline produced a garbled duplicate obligation

`task-01` yielded two obligations:

- `changed-rating-justifies-itself` [functional] — *"A rating it moves must rest
  on one of the changes it was given."* Carried from run 5, re-typed from
  `invariant` to `functional`. Duplicates `constraint-04`.
- `changed-test-evidence-rating-justify-itself` [test_demand] — *"A changed
  test-evidence rating justify itself."* **New, and ungrammatical.** The
  decomposer stripped the imperative "Make" from my headline without repairing
  the verb, and typed the result as a demand for a test.

Compare run 5, whose headline was also imperative and produced two clean,
grammatical obligations. So the imperative mood is not itself the trigger.

**Disposition: tool defect, queued as a filing under #181.** Not reworded. The
tie-break in `CLAUDE.md` is to rewrite when the tool's response makes me regret
my wording, and it does not — *"Make a changed test-evidence rating justify
itself"* is ordinary English and a Task headline restating its Constraints is the
normal shape of these files, run 5 included. Rewording here would be tuning the
input around a grammatical failure in the decomposer, which is the thing the
invariant forbids. The cost is real and downstream: a garbled duplicate typed
`test_demand` will attract its own mapping and judgement at Gate 2.

## Finding 2 — the linking triangle went unreconciled again

> answers contradict each other: these obligations are linked transitively but at
> least one pair among them was denied, so none of them were merged
>
> affected: `stored-rating-and-changes-recorded-with-judgement-request`,
> `changed-criterion-gets-stored-rating-and-dependency-changes`,
> `stored-rating-and-dependency-changes-in-request`

`constraint-03` and `completion-03` say the same thing in the same words, so
their two obligations are a genuine redundancy the linker should have collapsed.
`completion-02` is the third corner.

**Disposition: known tool defect, already filed as a comment on #242.** This is
the same unreconciled-triangle shape #251's runs 3 and 5 hit, and #251's Gate 1
accepted it as a residual redundancy rather than an invented or missing
obligation. Recording this instance against the existing filing; no new item.

Partly authored by me, and worth being honest about: the Completion expectations
in these task files deliberately mirror the Constraints, which manufactures the
near-duplicate pairs the linker then has to collapse. That is the established
shape of the format, not something #292 introduced.

## Finding 3 — a decompose call reported its stage as `unknown`

The run's own usage table:

```
  stage                                 calls  prompt  output  cached  this run  recorded
  decompose           1 (1 live / 0 replayed)   6,481     734    0.0%   $0.0082   $0.0082
  obligation linking  2 (2 live / 0 replayed)   1,791     127    0.0%   $0.0013   $0.0013
  unknown             1 (1 live / 0 replayed)     881      48    0.0%   $0.0009   $0.0009
```

#285 landed the constraint *"No model call the review pipeline issues reports its
stage as unknown"* along with `tests/test_stage_attribution.py`, which carries
both an AST scan over every `complete`/`embed` call site in `src/acceptance/`
(excluding `benchmark/`) and a wiring test asserting a real `run_review` leaves
no call unattributed. Both pass, and yet a live `decompose` produced an `unknown`
row — so there is a call the scan and the wiring test between them do not see.

The call is `align_obligations()` at `benchmark/alignment.py:77`, which passes no
`stage=`, so `ModelClient._observe_call` (`llm.py:405`) labels it
`UNKNOWN_STAGE`. It is reached from **product** code: `requirement/carry.py:166`
imports `acceptance.benchmark.alignment` inside `plan_carry()` and calls it at
`:171`, guarded at `:165` by a prior ledger entry plus unmatched residue on both
sides.

So there are two defects here, and the second is the larger one: the review path
depends on the measurement harness. `align_obligations`' own docstring
(`alignment.py:17-18`) says it "runs against known ground truth, not in the
product's own review path", and `CLAUDE.md` says `benchmark/` "is not part of a
review run". Both are false as written.

**Why the guard is green.** The AST scan (`tests/test_stage_attribution.py:88`)
excludes `benchmark/` **by path**, so the site is outside what it polices — and
the in-function import would defeat a per-module scan anyway. The wiring test
(`:179`) runs a real `run_review` but passes no ledger prior, so `plan_carry`
returns at `carry.py:115-119` before reaching the guard. The one path that
reaches the defect is the one path the wiring test does not take.

**Why it now fires on nearly every run.** The guard needs a prior ledger, which
`--continue` supplies. #251's triage changed `CLAUDE.md` to require `--continue`
on every gate re-run, so a rare condition became the default one.

**Disposition: tool defect, queued as a filing under #184.** Not acted on: it is
outside #292's scope, and it touches `requirement/carry.py::plan_carry`, which
#291 rewrites on its unpushed branch.

## Conclusion

Gate 1 passes on the substance — the obligation set is accurate and complete for
#292, with zero open questions. Two decomposition defects and one stage
attribution defect are queued rather than acted on. Awaiting the human's
confirmation of the breakdown, which is what the gate actually requires.
