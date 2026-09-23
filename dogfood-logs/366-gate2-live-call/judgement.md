# #366 — the one live call with a reasoning effort set

Approved by the human at 2026-09-23 before it was made. One call, $0.0015, 9.2s,
on `openai/gpt-5.4`, stage `mutation verification: defect match`, effort `low`.
Made from commit `320091e` with `live_call.py` beside this file. The raw
transcript was written to a scratch store and is not committed: it embeds the
full request.

**The effort reached the provider.** `usage.reasoning_tokens` is 37, above zero.
The pre-call check passed: LiteLLM reported the effort as kept. No comparison
call without an effort was made, so what this model reports with no reasoning
was not measured here.

**The reply parsed against its schema** (`Answer`, strict), and is correct:
1,234,567 = 7 × 176,366 + 5.

**Provenance does not claim temperature 0.** `controls_applied` and
`stage_controls` both record `temperature: null`, since LiteLLM drops temperature
from an OpenAI reasoning call, and the review's determinism reads `unpinned`.
The seed of 0 is the harness's default seed and was kept.

**The footer shows the reasoning column**, with 37 of the call's 86 output
tokens, and the cost of $0.0015 is LiteLLM's price for all 86.
