Found during #415 (report the Claude credits each run spends), discussing whether LiteLLM is still the right layer.

## The problem

Every model call goes through LiteLLM. Its value is breadth — many providers behind one call — and that still matters: a user may be constrained to particular providers, and cheaper options such as open-weight models are worth measuring. But on our main path it hides or guesses facts we then reconstruct:

- **Cost.** `litellm.completion_cost` prices a direct call, so #414 records half of it for a batched call by hand.
- **Tokens.** `litellm.token_counter` falls back to OpenAI's tokenizer for Claude, so the count that decides whether an opening gets a cache breakpoint is an estimate (queued at #414's Gate 1; the gap is unmeasured).
- **Controls.** Temperature and seed are dropped for Claude without notice, which is why the review records `controls_in_force`.
- **Request format.** It translates our schema into Anthropic's `output_config.format`; how that interacts with caching was learned from Anthropic's docs (#324, where every stage sends a unique schema and nothing caches).
- **Provider.** It routes a bare `claude-…` to Anthropic by its own inference. #415 closed this by refusing model names with no `provider/` prefix.
- **Coupling.** Tests patch LiteLLM internals (`litellm.llms.anthropic.chat.handler.get_httpx_client`), and replay needs lazy-import care to stay free of it.

Batches already bypass it: LiteLLM cannot create an Anthropic batch, so #414 added the `anthropic` SDK.

## Proposal

- **One small interface of our own, one adapter per provider**, chosen by the provider the model name states (`llm.provider_of`, from #415). The provider decision then picks the code path, not only the cache and batch behaviour.
- **A native Anthropic adapter** on the official SDK for the main path, where batching, cache breakpoints, exact token counts and exact cost matter.
- **A general adapter through LiteLLM** for every other provider, so a user's choice keeps working without new code. Most open-weight hosts (vLLM, Ollama, Together, Fireworks) speak the OpenAI-style API, which LiteLLM covers. A native adapter is written only for a provider used heavily enough that exactness pays.
- **Each adapter declares its provider's capabilities** — structured output, cache breakpoints, batching, whether seed and temperature are honoured, where prices come from — instead of the client inferring them from the model name.

## Rejected alternatives

- **Anthropic's SDK only.** Exact on Claude, but drops every other provider, which a user's constraints or a cost comparison may require.
- **Stay on LiteLLM everywhere.** Keeps breadth, keeps every guess listed above.

## Cost

Moving the Anthropic path off LiteLLM changes every request's bytes, so the whole transcript corpus re-records at once and benchmark figures before and after are not comparable — the shared-request-assembly case in `CLAUDE.md`. Do it once, deliberately, not inside another task. The general adapter alone changes nothing that is recorded today.

## Acceptance

- A Claude run goes through the native adapter: its recorded usage and cost come from Anthropic's response, with no hand correction for batches.
- A run on a provider with no native adapter completes through the general adapter.
- Cache breakpoints, batching and control handling are read from the adapter's declared capabilities, not from the model name.
- The corpus is re-recorded once, and the re-recording is noted where benchmark figures are compared.
