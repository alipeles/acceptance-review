# #415 Gate 2, run 3 — continuing `27526bbc2830607e`, base 9527671, head 48220c4

**Not clean.** INCOMPLETE: four obligations partially supported (two moved from
strongly supported), one "no plausible defect", two `in_service` unrequested
changes, eleven "already present" claims.

## Real, fixed in 4fa0daa

- `provider-parse-accepts-empty-head` / `empty-provider-prefix-accepted`:
  `/claude-x` gave provider `''`, which passed the configuration check. Now None.
- `provider-not-recorded-on-call` / `provider-field-missing-on-calls` (survived,
  provider stamped only on live calls): no test that a replayed call carries its
  provider. Added.
- `other-providers-by-subtraction` / `anthropic-figure-missing-from-rendered-table`:
  the "other providers" figure was total minus Anthropic and could print
  `-0.0000`. Now summed directly.

## Not defects

- `provider-read-from-returned-model-name`, `provider-label-from-record-model-not-request-model`
  (survived): equivalent edits. A transcript record has no top-level `model`, so
  `record.get("model") or model` is `model`. No test can tell them apart.
- `calls-after-report-omitted` and the recommended tests for obligations 1 and 2:
  ask for model calls made while the `InstabilityReport` is assembled. None are;
  assembly is pure. The scenario cannot happen.
- Recommended tests for obligations 7 and 8: "every other model-name field on
  `RunConfig`". There are none beyond `model`, `embedding_model` and
  `stage_models`. A `ModelClient` built directly bypasses `RunConfig` by design;
  it is the internal type, `RunConfig` is the configuration surface.
- `summarize-drops-calls-by-stage` (survived): the same defect run 1 asked a test
  for and run 2 rated the test unrequested. Left untested; the contradiction is
  the finding.
- "Already present", all **false** or contrary to an owner decision:
  `anthropic-spend-gated-on-served-from` (this-run vs recorded is the design),
  `report-printed-to-stderr-only` (stderr keeps stdout byte-identical),
  `provider-from-model-name-prefix-only` and `provider-attribution-by-prefix-only`
  (bare names are refused by owner decision), `batching-and-markers-decided-by-different-tests`
  (asks the footer to re-derive the provider from the name: the exact thing #415
  removed), `usage-trusts-optional-provider-key` (every observed call carries the
  key), `provider-rederived-per-consumer` (every consumer calls one pure function
  of the configured name; that is one decision). Added to the #424 draft.
- Unrequested, both `in_service`: refusing provider-less names (owner decision
  2026-10-26) and printing the footer in `finally` (run 2's own recommendation).

## Separately

`tests/test_llm_batch.py::test_clients_built_from_one_configuration_share_one_batch`
failed once (`[1, 9]` batches, not `[10]`) and passed five reruns. Timing in
#414's gather window, not this change. Queued.
