# Judgement — injection audit v7 (what the code does, asked before the edit)

Judged 2026-09-16 by a helper agent reading every edit and every
already-present claim in `injection-audit-v7.md` against the source at
`518f876`, with no tests run, by the same categories as the v5 and v6
judgements. The calls are the agent's; I have not re-checked them one by one.

What changed from v6, and nothing else: the edit-building answer states first
whether the code does the EXPECTED or the DEFECTIVE behaviour and that answer
decides what the edit means (`fa4b267`); a "defective" answer is a finding whose
edit is run as a repair; the breadth check refuses a result that fails more than
7.5% of candidate tests (`dcca767`). Same defect list as v6 (its
`defects.json`), for 22 of its 25 criteria — the three the human is adjudicating
by hand are left out: `recorded-at-strongest-evidence-tier`,
`stop-review-on-failing-candidate-test`, `candidate-tests-run-once-before-changes`.
Edits on `openai/gpt-5.4`. v6 is recounted on the same 22 criteria below.

## The table

"Counted" is every kill and survival — the results the review would record. v7
also refused 8 edits after their run; those are shown separately.

| | v6, 22 criteria | v7 |
|---|---|---|
| edits counted | 58 | 44 |
| put the named defect into the code | 25 (43%) | 25 (57%) |
| repair a defect the code already had | 7 | 3 |
| change something other than the defect | 16 | 12 |
| break far more than the defect | 10 | 4 |
| real kills | 20 of 46 (43%) | 23 of 36 (64%) |
| real survivals (genuine test gaps) | 5 of 12 | 2 of 8 |
| edits refused by the checks after the run | — | 8, all correctly |
| already-present claims | — | 12: 9 right, 3 wrong |

Of the 8 refused: 5 by the breadth check (79, 79, 42, 29, 26 tests failed), 3 by
the missing-name check. The agent judged 6 as breaking far more, 1 as changing
something else, 1 as a repair — no genuine injection was refused.

**The previous pathology did not recur.** None of the 52 edits was byte-identical
to its input, and the model declined nothing: 52 answered "expected", 12
"defective", 0 "cannot_tell", 0 declines.

## What it shows

- **Credible kills rose from 43% to 64%**, from fewer repairs (7 → 3) and the
  breadth and missing-name checks catching crashers (10 → 4 still counted).
- **Edits that change the wrong thing barely moved (16 → 12).** Nothing added
  today targets them; the verifier was meant to, and it is not adopted.
- **Survivals got no better, and fewer are real (5 of 12 → 2 of 8).** Most bad
  survivals are edits that change nothing the tests could see.
- **Repairs are unreliable.** 9 of 12 claims are right, but only 5 repair edits
  actually make the code do the expected behaviour, so the repair run's
  corroboration is weak evidence. The agent found at least three repairs that
  crash (a duplicated argument, a line-0 descriptor, a missing attribute), and a
  crash makes tests fail on the repair for a reason that says nothing about the
  claim. 9 of the 12 repair runs recorded a failing test; I have not checked
  which of those 9 are the crashing ones.

## Already-present claims

Right: `execution-tier-only-runs-when-explicitly-enabled`,
`halted-baseline-prevents-static-fallback`, `static-judgement-skipped-when-execution-runs`,
`baseline-halt-prevents-execution`, `execution-flag-off-by-default`,
`no-search-for-smaller-edit`, `region-bounds-can-overconstrain-minimality`,
`mutation-attempt-tier-returns-stronger-evidence`, `pair-verdict-tier-default-stays-static`.

Wrong: `descriptor-declines-are-not-mechanically-enforced`,
`line-execution-recording-still-present`, `execution-tier-alters-candidate-selection`.

Several right claims are about execution being opt-in or about tier wording,
which sit close to the three criteria left out; the agent notes the
`weaker-tier-evidence` criterion looks suspect for the same reason.

## Real test gaps among the survivals

- `mutation-block-omits-injected-text-for-unsettled-attempts` — no test renders a
  `not_attempted` defect that has a descriptor.
- `prediction-language-still-used-in-recorded-conclusion` — low stakes.

Also a gap found in passing: `tests/test_cli_execution.py` replaces `run_check`,
so nothing checks that `run_check` hands the execution settings to the pipeline.
