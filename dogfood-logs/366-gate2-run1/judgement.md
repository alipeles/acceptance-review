# #366 Gate 2, run 1 — judgement

Run `c07948e3cd161d42`, continuing `ed55dde4b2bce366`, base `01c4eb3`, head
`d66be1a`, $0.4838.

**Not clean.** Verdict `NO-MATERIAL-GAPS`: all 14 obligations addressed, the 12
that take test evidence strongly supported, the two scope-exclusion obligations
confirmed from code. No open questions, no recommended tests. Six unrequested
changes, all `in_service`. What stops it is the "Candidate tests set aside"
section.

## Set aside: four tests reached the network — real, my defect, fixed

`test_litellm_itself_is_what_stops_a_model_that_takes_no_effort`,
`test_litellm_keeps_the_effort_and_drops_the_temperature_on_gpt_5_4`,
`test_the_cost_of_a_reasoning_call_includes_its_reasoning_tokens` (all new), and
the older `tests/test_llm.py::test_the_live_call_lets_litellm_discard_controls_a_provider_rejects`.
Each connected to `raw.githubusercontent.com`: LiteLLM downloads its model price
table on first use. The cost test is the sole evidence for obligation 12
(`include-reasoning-tokens-in-reported-cost`), so its rating rested on a test the
sandbox could not run.

Fix: `tests/conftest.py` sets `LITELLM_LOCAL_MODEL_COST_MAP=True`, which
`litellm_core_utils/get_model_cost_map.py` reads to load the bundled table with
no fetch. The offline probe gives identical answers under it for all six
model/effort cases tried.

## Set aside: one test fails only in the review's repo copy — tool defect, queued

`tests/benchmark/test_rating_regression.py::test_scoring_goes_through_the_shared_benchmark_path`
fails in the copy with `UnresolvableRevisionError` for `4d13ba1`, which resolves
in the real repo. Unrelated to this change; evidences none of its obligations.
Drafted in `docs/DEFERRED.md` as a filing, unparented.

## Unrequested changes — all `in_service`, agreed

Item 6 says the relaxed Constraints assertion in `test_task_file.py` "is
unrelated to the listed obligations" while marking it `in_service`. It is
unrelated to the mandate; it is needed only because this task's committed task
file has no Constraints section and CI would fail on it. Raised at the gate.

## Mapping sanity (DR-164, the record on partitioning the mapping request)

Every test-evidenced obligation lists at least one mapped test, and the pair
section shows 4 pairs put to the model per defect with the rest skipped once
covered, not an empty mapping.
