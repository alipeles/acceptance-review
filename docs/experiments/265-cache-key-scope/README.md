# What is in the prompt-cache key? — #265

Run 2026-08-20 against `openai/gpt-5.4-mini`, seed 0, temperature 0.0, nonce
`r1787255025`. Nine live calls; script and full output committed beside this file.

```bash
.venv/bin/python docs/experiments/265-cache-key-scope/cache_key_scope.py
```

**Re-running is safe but never free**, and each run must use a fresh nonce — see
*Reproducing* at the end, which is a trap this experiment fell into once.

## Why it was run

#265's change makes coverage classification and unrequested-change detection open
with a **byte-identical ~70k-token diff block**, issued seconds apart in one
review run. Measured at #265's Gate 2, the second reused **none** of it. The bytes
were identical and the order was right, so the messages were not what kept them
apart.

## Result

| case | schema | prompt | cached |
|---|---|---|---|
| `cold` | `_Coverage` | 9,998 | 0 (0.0%) |
| `repeat_same` | `_Coverage` | 9,998 | **9,472 (94.7%)** |
| `same_schema_new_tail` | `_Coverage` | 9,996 | **9,472 (94.8%)** |
| `different_schema` | `_Detections` | 10,004 | 0 (0.0%) |
| `different_schema_same_shape` | `_Renamed` | 9,999 | 0 (0.0%) |
| `different_prefix` | `_Coverage` | 9,991 | 0 (0.0%) |
| `constrained_enum_cold` | `_Mappings` | 10,021 | 0 (0.0%) |
| `constrained_enum_same` | `_Mappings` | 10,017 | **9,472 (94.6%)** |
| `constrained_enum_differs` | `_Mappings` | 10,017 | 0 (0.0%) |

Both controls behaved: an identical repeat reused 94.7%, and a different opening
reused nothing.

## Two findings, and the second is the one that bites

**1. The response schema is in the cache key, and its NAME alone breaks reuse.**
`different_schema_same_shape` sends byte-identical messages and a schema with
byte-identical *fields*, differing only in the name `_Renamed` — and reused
nothing. Since every stage sends a different response model, **cross-stage prefix
sharing is impossible by construction.**

**2. The per-call id enum breaks it too, so sibling calls cannot share either.**
`constrained_enum_same` and `constrained_enum_differs` send the same schema name,
the same fields, and the same opening. They differ only in the *values* of an id
enum — `["a-1","a-2","a-3"]` against `["b-1","b-2","b-3"]`. The first reused
94.6%; the second reused nothing.

That is exactly what `supplied_ids.constrain` does on every partitioned stage: it
restricts each id field to a `Literal` of the ids *that call* supplied, so two
batches of one stage necessarily send different schemas. **Every batch of a
partitioned stage is a cache miss by construction.**

## What this explains, and what it costs

It explains **mapping's 4.5%** at #265's Gate 2 — 18 batches, each with a
different `test_id` enum, so each one a miss. It was the last unexplained number
in the original #265 comment ("3 of 464"), and it is not mysterious: the tool is
defeating its own cache with the mechanism that makes ids unrepresentable.

It also retires most of #265's stated scope:

- The three big stages — test recommendation, unrequested-change detection,
  coverage classification — issue **one call per run** each
  (`pipeline.py:351-359`), so they have no sibling to share with; and finding 1
  closes the cross-stage route. Nothing about prompt shape can make them cache.
- The four partitioned stages — mapping, discrimination, decompose, obligation
  linking — have siblings, but finding 2 says their siblings cannot share either
  while `constrain` is in the request.

**So prompt ordering cannot help any stage as things stand.** The ordering work
on `265-share-request-openings` is correct and is a precondition for reuse, but
it buys nothing on its own.

## Where the lever actually is

`same_schema_new_tail` at 94.8% and `constrained_enum_same` at 94.6% show the
provider will happily reuse a long opening across calls that differ in their
tail. What has to change is the *schema*, not the prompt:

- Take the id constraint out of the request and validate returned ids locally
  instead. That is a direct trade against #163, which put the enum in the schema
  so a foreign id would be unrepresentable rather than merely rejected —
  `supplied_ids` already does the local check as a backstop, so the question is
  whether the enum is still earning its cost.
- Or keep the enum **stable across a stage's batches** — supply every id to every
  call and let the batch scope only what the call must *answer for*, which is
  already how decomposition treats its registry (DR-204, #178).

The second is much the smaller change and does not give up #163's guarantee.
Neither is in scope for the mandate that produced this measurement.

## Caveats

- One model, one provider. The 1,024-token minimum and the retention window are
  model-dependent, and this says nothing about Anthropic, which uses explicit
  breakpoints rather than automatic prefix matching.
- The schema reaches the provider as `response_format`, which LiteLLM passes
  through. A provider that translates structured output differently — Anthropic
  takes it as tool use — may key it differently.
- `constrained_enum_*` uses a small synthetic enum. A real stage's enum is longer,
  which can only make the divergence earlier, not later.

## Reproducing

**Each run needs a fresh nonce, and the script defaults to one.** The second run
of this experiment was made minutes after the first and reported **94.9% on every
row, including both controls** — because the openings were still in the
provider's cache from the previous run. `verdict()` refuses to conclude when the
negative control hits, which is the only reason that run was not read as
"caching works everywhere". Pass `--nonce` explicitly only to re-send a recorded
run's exact prompts, and expect every row to hit if the provider still holds them.
