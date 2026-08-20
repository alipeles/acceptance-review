# Is the response schema in the prompt-cache key? — #265

Run 2026-08-20 against `openai/gpt-5.4-mini`, seed 0, temperature 0.0.
Six live calls; script and full output committed beside this file.

```bash
.venv/bin/python docs/experiments/265-cache-key-scope/cache_key_scope.py
```

## Why it was run

#265's change makes coverage classification and unrequested-change detection
open with a **byte-identical ~70k-token diff block**, issued seconds apart in one
review run. Measured at #265's Gate 2, the second reused **none** of it — both
reported 0.0% cached. The bytes were identical and the order was right, so the
messages were not what kept them apart.

## Result

| case | schema | prompt | cached |
|---|---|---|---|
| `cold` | `_Coverage` | 8,898 | 0 (0.0%) |
| `repeat_same` | `_Coverage` | 8,898 | **8,448 (94.9%)** |
| `same_schema_new_tail` | `_Coverage` | 8,896 | **8,448 (95.0%)** |
| `different_schema` | `_Detections` | 8,904 | 0 (0.0%) |
| `different_schema_same_shape` | `_Renamed` | 8,899 | 0 (0.0%) |
| `different_prefix` | `_Coverage` | 8,891 | 0 (0.0%) |

Both controls behaved: an identical repeat reused 94.9%, and a different opening
reused nothing.

**The response schema is in the cache key, and its NAME alone is enough to break
reuse.** `different_schema_same_shape` sends byte-identical messages and a schema
with byte-identical *fields*, differing only in the name `_Renamed` — and it
reused nothing.

## What follows

**Cross-stage prefix sharing is impossible by construction.** Every stage sends a
different response model, so no two stages can ever share a cached opening, no
matter how their messages are ordered. The 0.0% measured at Gate 2 is not a bug
in the ordering and cannot be fixed by more ordering.

That retires the reading in #265's own comment that the three big single-call
stages — test recommendation, unrequested-change detection, coverage
classification — need their invariant content hoisted. They issue **one call per
run** each (`pipeline.py:351-359`), so they have no sibling to share with, and
the cross-stage route is now known to be closed. **Nothing about prompt shape can
make those three cache.** Their only route is issuing more than one call that
shares an opening, which is batch composition, not ordering.

**The ordering change is still right, and the number that proves it is
`same_schema_new_tail`: 95.0%.** Identical opening, different trailing message,
same schema — which is exactly a sibling call in a partitioned stage. That is the
case #265's change creates for mapping, discrimination, decompose and obligation
linking, and it matches the 84–93% #191 reported on its own branch.

So the lever works; it was aimed at the wrong stages.

## Caveats

- One model, one provider, one run. `cache_read_input_token_cost` and the
  1,024-token minimum are model-dependent and this says nothing about Anthropic,
  which uses explicit breakpoints rather than automatic prefix matching.
- It does not explain mapping's **4.5%** at Gate 2. Mapping is partitioned into
  18 calls with a shared opening, so on this result it should have done far
  better. Something else is limiting it, and that is the next question rather
  than a settled one.
- The schema reaches the provider as `response_format`, which LiteLLM passes
  through. A provider that translates structured output differently — Anthropic
  takes it as tool use — may key it differently too.
