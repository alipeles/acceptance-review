# Judgement — #217 Gate 2 run 1

`6ae97fd` → `76b847b`. **Not clean.** INCOMPLETE: 1 obligation not addressed,
11 with non-discriminating test evidence.

## The true positive that mattered

`obligation-discriminated-union` — *"Model `_RequirementDisposition` as a
discriminated union keyed by its disposition field"* — **code evidence: not
addressed.** Correct. The implementation uses a plain `Union`, deliberately: a
pydantic tagged union renders `oneOf` + `discriminator` and OpenAI strict mode
accepts neither, and `inline_schema_refs` would leave the discriminator mapping
pointing at `$defs` it had just inlined.

Disposition: **task-file wording corrected** (the sanctioned rewrite). The
constraint named a pydantic mechanism that turned out to be unusable; it now
states the requirement — one shape per disposition, carrying only its own
payload, unambiguous at parse via literal tags. The wording changed, the output
did not.

## Real test gaps, all closed in `007966f`

Unknown requirement id rejected; requirement disposed twice rejected;
open-question disposition naming no produced question rejected; the disposition
set is exactly three with no executable reference to the removed value; DR-202
records the amendment.

## Unrequested changes

One **[separable]**: the union walk added to `supplied_ids.py`. Investigated, not
waved off — it is load-bearing (without it the `requirement_id` constraint
silently vanishes under the new shape) but the mandate genuinely did not ask for
it, and it had **no test at all**. Both fixed: a constraint added to the task
file, and `test_a_union_of_item_shapes_constrains_every_member` added.

The three **[in_service]** entries are accurate and accepted.
