# Judgement — #316 Gate 1, run 2

Run `4b869f02db47b1c5`, continuing `0bf2214b000f9f93`. 0 derived, 14 carried, 1
revised; 4 decompose calls, $0.0260. No open questions raised.

**Not accepted**, but close. Only the reworded Task requirement was re-derived;
the other 14 requirements were carried, which is the carry behaving as it should.

## Findings

**1. Run 1's invented obligations are gone.** Rewriting the Task narrative so the
background sits in a relative clause dropped task-01 from eight obligations to
three, and the obligation that contradicted exclusion-01 did not reappear. That
confirms finding 1 of run 1 as a wording problem I could fix, not a defect that
survives good input.

**2. A three-item compound subject was split inconsistently, and the most
important item was dropped.** My sentence read "The rating a criterion gets for
its test evidence, the tests the review prescribes and the conclusion the review
reaches are all derived from the judgements…". Item 2 became
`prescribed-tests` — "The review prescribes tests", contentless, typed
`test_demand`. Item 3 became `conclusion-derived-from-recorded-judgements`,
correct. **Item 1, the rating, produced no obligation at all** — and the rating is
the primary requirement of the whole task. Its substance is still reachable
through constraint-01's `rating-by-coverage-completeness`, so nothing was lost
from the set as a whole, but one of three parallel items of one sentence
silently vanished with no diagnostic.

Disposition: split the compound subject into three sentences and re-run. Same
family as #212; recorded there rather than filed separately.

## Disposition

Rewrite the Task section into one requirement per sentence, re-run with
`--continue 4b869f02db47b1c5`.
