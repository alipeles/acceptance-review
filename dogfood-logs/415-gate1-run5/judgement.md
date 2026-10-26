# #415 Gate 1, run 5 — `03257667299320cb`, at cbbf50d, continuing run 4

7 requirements, 11 obligations, no open questions.

## Why this run exists

Gate 2 run 1 asked whether `is_claude` was too narrow. Looking into it showed
the real problem (see `dogfood-logs/415-gate2-run1/judgement.md`): the provider
a call goes to is decided once, when the model is configured, and three places
in the client re-derived it from the model name, each its own way. The owner
asked for the root fix inside #415. task-02 was reworded from "Claude models" to
calls billed to Anthropic's own API, and a new paragraph (task-03) requires one
provider decision that cache breakpoints, batching and spend all read.

## Findings

- task-03 yields `provider-routing-by-model-name` and
  `provider-decision-single-source`. Accurate.
- task-02 yields `table-separates-anthropic-spend` and
  `anthropic-credits-own-figure`; the second restates the first, from the
  "so the Anthropic credits … can be read off" clause. Same shape as #273 (an
  explicit obligation restating another explicit obligation is not reconciled
  with it), already documented there by the comment filed at this task's Gate 1
  (issuecomment-6405784683). Recorded against it; no new filing.
- Everything else carried and accurate. None missing.

## Disposition

Accurate apart from the known duplicate. Proceeded to code.
