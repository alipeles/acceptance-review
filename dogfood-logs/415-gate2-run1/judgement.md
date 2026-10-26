# #415 Gate 2, run 1 — `0abf1ff71bd245a8`, base 9527671, head becfffd

**Not clean.** INCOMPLETE: four obligations partially supported, one unrequested
change, and three "defects the delivered code already has" needing human review.

## The headline

**The run found something significant but did not identify the core issue.**
Its claim `claude-spend-separate-figure/is-claude-prefix-match-too-narrow` said
`usage.py::is_claude` misses names like `anthropic.claude-…` and `Claude-…`, and
proposed widening the match to "claude anywhere, case-insensitive". The
observation was right: the function was wrong. The diagnosis and the repair
were not. Following it up with the owner showed:

- Model names are not canonical. They are free LiteLLM routing strings
  (`provider/model`), recorded as sent.
- The provider a call goes to is an intentional decision made once, at
  configuration. The client then re-derived it from the name in three places,
  each by its own rule: cache breakpoints and batching
  (`llm.py::_needs_explicit_marker`, first segment is `anthropic`), and spend
  (`usage.py::is_claude`, last segment starts with `claude`). They already
  disagreed on `vertex_ai/claude-…`.
- "Claude credits" was the wrong quantity: a Claude call through Bedrock or
  Vertex is billed by AWS or Google. The tool's repair would have counted those
  as Anthropic credits — more wrong, not less.

The core issue was a design one — reconstructing a decision with pattern
matching instead of carrying it — and the tool saw only a symptom. The owner
identified it. Fixed in #415: `llm.provider_of` is the one decision, each
observed call records its `provider`, and the spend footer reads that field.

## Other findings

Real test gaps, fixed in cbbf50d (each confirmed by fault injection):

- `perturbed-run-client-not-collected` (and `run-once-client-not-registered-on-all-draws`,
  `instability-clients-not-all-collected`, same injected line): the wiring test
  ran with no perturbation. Now it does, and requires the printed table to equal
  `render(summarize(...))` over every client built.
- `dedupe-by-id-drops-calls`: no test shared one client across draws. Added.
- `table-format-differs-from-check-decompose`: pinned by the exact-equality assertion.
- `claude-line-missing-on-some-render-paths`: `report([])` now tested.
- `summarize-drops-calls-without-usage`: a call naming no stage is now tested.

Unrequested change: the `cli.py` switch to the shared `report` helper, rated
`in_service` but needed by no obligation. Reverted.

"Defects already present" claims 2 and 3
(`dedup-by-identity-drops-or-duplicates-calls`,
`identity-dedup-undercounts-distinct-clients`): **I believe both are false.**
They assume two client objects sharing one call log; every `ModelClient` creates
its own list in `__init__`, and `observed_calls` returns copies, so the proposed
repair (dedupe by each call's `id()`) never matches and would double count the
shared-client case `test_a_client_every_draw_shares_has_its_calls_counted_once`
pins. Same shape as #424 (a defect judge asserts a defect "already present" that
the code rules out). Queued as a comment on #424 in `docs/DEFERRED.md`.
