# #415 Gate 2, run 2 — `27526bbc2830607e`, base 9527671, head 1f9af56

**Not clean.** INCOMPLETE: four obligations partially supported, one rated "no
plausible defect", one unrequested change, nine "already present" claims.

## Real, fixed in 9127400 and 48220c4

- `batch-gate-bypasses-marker-decision` / `batch-routing-divergent-check`:
  batching repeated `provider_of(...) == ANTHROPIC` inline beside the cache-marker
  check. Both now ask `llm.is_anthropic_api`.
- `provider-field-missing-on-some-call-records` (survived): no test that an
  embedding call records its provider. Added; fault-injected.
- `usage-report-not-on-all-paths` (survived, `if not batch:` around the footer):
  the wiring test now runs with `batch` False and True; fault-injected.
- `footer-not-printed-when-draw-fails` (recommended test): the footer moved into
  `finally`; tested with a draw that raises.
- `no-explicit-other-provider-figure`: an "other providers" line added.
- `bare-claude-name-not-anthropic` and three near-duplicates: real gap, wrong
  repair. The repair (treat bare `claude…` as Anthropic) is the guessing the owner
  ruled out. The owner chose to refuse names with no provider prefix at
  configuration (48220c4).

## Tool over-reach

- `provider-prefix-case-sensitive-exact` and `provider-match-case-sensitive-exact`:
  **false.** I verified LiteLLM rejects `Anthropic/…` and ` anthropic/…` with
  `BadRequestError`, so no such call is made or billed. Added to the #424 draft.
- Obligation 9 (`spend-excluded-from-review-state-and-report`) rated "no plausible
  defect" though tests pin it (`test_the_breakdown_never_reaches_the_rendered_report`,
  the cheap/dear identical-state test). Same shape as the queued #180 comment
  (criteria drop to "no plausible defect" on unchanged code).
- Unrequested: `test_a_call_that_names_no_stage_is_still_counted` rated
  `separable`. I added it because run 1's enumerator asked for exactly that.
  Removed. The two stages contradict each other across runs.
