# Judgement — #167 Gate 2, run 4 (`52c52b8`)

Verdict: **INCOMPLETE**. 3 of 12 below `strongly supported`; a fourth distinct set.
Run after fixing all three of run 3's real gaps.

| obligation | judgement |
|---|---|
| `preserve-prose-structured-fields` | **REAL.** The test asserted 4 of the 6 §9.5 fields — `required_inputs` and `repo_conventions` were unasserted, so a regression compressing either to a terse token would pass. Fixing it also exposed that the `repo_conventions` fixture was a bare path (`tests/test_thing.py`), not prose, which made a prose assertion vacuous. Fixed in `dd0a6a5`. |
| `no-speculative-writing` | **Not real.** Both tests the recommendation asks for now exist and are mapped (`test_retrieval_writes_nothing_into_the_repo` snapshots the tree, `test_retrieval_makes_no_model_call` covers the call). Its `detects` clause is self-contradictory: *"makes a model call during retrieval but does not write anything."* |
| `empty-result-for-missing-criterion-recommendation` | **Not real.** The recommendation describes exactly what `test_recommendation_for_an_unknown_criterion_is_empty_not_an_error` does — populated store, absent criterion, empty result rather than an error. |

Three of four rounds so far have surfaced at least one real gap, so the churn is
not pure noise; but two of three findings here were already covered, which is the
first clear evidence of the **false-positive** direction alongside #180's
false negatives.
