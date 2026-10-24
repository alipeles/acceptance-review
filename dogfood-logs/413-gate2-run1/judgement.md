# 413 Gate 2, run 1 — judgement

Run `ea62a34bb02a6166`, continuing Gate 1's `6bc7ccd4832f4975`. The first check on
Claude Sonnet 5.5 for every stage: $2.93 on 255 live calls, 0% cached on every
stage. `tests/fixtures/transcripts/` was left out of the diff by the owner's
decision (`.acceptance/ignore`, main 4441f97).

Verdict INCOMPLETE. Not clean.

## Findings

1. **Unrequested change: a weakened assertion** — real. My edit to
   `test_a_recorded_call_completed_against_a_provider_that_rejects_our_controls`
   replaced the disposition-enum check with "parses to a dict". Fixed by checking
   every Claude recording against the schema it sent: required fields, no extra
   fields, enum values. The disposition schema's enum is the same three values the
   old check listed.
2. **`provenance-records-claude-applied-neither-temperature-nor-seed`, partially
   supported (3 of 5)** — real. Its recommendation asks for the provenance as
   saved in the review state, not only the in-memory object. Added
   `tests/test_cli.py::test_a_default_cli_run_on_claude_records_both_controls_as_not_applied`,
   which asks LiteLLM itself.
3. **`prompt-test-assertions-hold-on-claude-answers`, partially supported (2 of 5)**
   — real. Its recommendation: a prompt test pinning another model would leave
   prompts without Claude coverage. Added
   `test_every_recording_the_default_replays_is_on_the_default_model`.
4. **`recorded-claude-run-replays-without-live-call` partially addressed,
   `recorded-runs-byte-identical-review-state` unclear,
   `claude-schema-mismatch-typed-error` not addressed** — the behaviour already
   held before this change, and its tests (`tests/test_llm.py`,
   `tests/test_determinism.py`) were outside the diff, pinned to
   `anthropic/claude-sonnet-5`. Addressed by moving those tests onto
   `DEFAULT_MODEL`, and adding a typed-error case run on both providers. If run 2
   still reports them not addressed, that is the tool reading "no code change" as
   "not done" for a property that already held, and needs a filing.
5. **`request-temperature-and-seed-zero`, "no plausible defect"** — not a finding;
   recorded only.

0% cache hits on Claude across all stages is queued for #414 (cache breakpoints).
