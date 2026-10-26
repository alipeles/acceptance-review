# Task

When the benchmark's instability measurement finishes, it prints the per-stage
usage table that `acceptance check` and `acceptance decompose` already print,
covering every model call the measurement made, with live and replayed calls
counted apart.

The table shows what the run spent on calls billed to Anthropic's own API
separately from what it spent on any other provider, so the Anthropic credits a
run consumed can be read off as a figure of its own. A call sent through the
Message Batches API counts at the price it was billed at.

Which provider a call goes to is the one its configured model name states, and
every part of the client that depends on the provider reads that one decision —
whether a request carries cache breakpoints, whether it can be batched, and whose
credits it spent — rather than each guessing from the model name in its own way.

Spend stays out of the review state and the rendered report, as it is today.

## Scope exclusions
- Checking the Console tier's rate limits against run sizes.
- Changing how any call is priced when it is recorded.
- Enforcing a spending limit or stopping a run that spends too much.
