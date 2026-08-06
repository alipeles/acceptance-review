# Task
DR-202 decision 3 gives a requirement exactly one of three dispositions, each
carrying something: yielded obligations, deliberately yields none with a reason,
or raised an open question instead. The implementation added a fourth,
`UNDISPOSED`, carrying none of them, and reached it two ways: a response that
never mentioned a requirement, and a response that labelled a requirement
`yielded` while naming no obligations.

Both are malformed responses, and both are currently absorbed as soft findings.
`_requirement_map` discards the reason the response supplied, substitutes a
diagnostic string of its own, and lets the run continue to a verdict on an
answer that did not account for the mandate.

The registry of requirements is derived deterministically from the parse, and
the code iterates over that registry. Dropping a requirement is therefore not a
possible outcome — the only possible bad outcome is a response of poor quality.
Make that true in the types: every requirement carries one of exactly three
dispositions, each structurally required to carry its own payload, and a
response that fails to account for every requirement does not parse. Remove the
fourth disposition entirely.

## Constraints
- A requirement disposition is one of exactly three: yielded obligations,
  no obligations needed with a reason, or an open question that prevents an
  answer.
- `Disposition` has no `UNDISPOSED` value.
- `_RequirementDisposition` is a union of one shape per disposition, each
  carrying only the payload its own disposition defines.
- The union is unambiguous at parse: each shape names its disposition as a
  literal value.
- The schema sent to the model uses only keywords OpenAI strict mode accepts.
- A `yielded` disposition carries at least one obligation id.
- A `no_obligation` disposition carries a reason that is not empty.
- An `open_question` disposition carries at least one open-question id.
- A response labelling a requirement `yielded` while naming no obligation id
  fails to parse.
- A response labelling a requirement `no_obligation` with an empty reason fails
  to parse.
- A response that omits any requirement in the registry is rejected.
- A response that names a requirement id absent from the registry is rejected.
- A rejected response produces no `RequirementMap`.
- The JSON schema sent to the model cannot express a `yielded` disposition with
  zero obligation ids.
- The reason a response supplies for declining a requirement is preserved rather
  than replaced by a diagnostic string.
- The helper that restricts an id field to the ids a call supplied keeps working
  when the response model's item type is a union, so the requirement-id
  constraint survives the new shape.
- Typed schemas are pydantic models, as the rest of the repository defines them.
- Tests issue no live model calls.

## Scope exclusions
- The decomposer declining to yield obligations for scope exclusions, against
  the instruction already in the decompose prompt. That is a prompt defect
  tracked separately and costs a transcript re-record.
- Changing the decompose prompt text.
- Retrying or repairing a rejected response.
- Nested-bullet and multi-paragraph parse coverage, which is #216.
- Whether mandate coverage bounds the completion verdict, which is #214.
- Aligning requirement ids across two versions of a task file, which is #209.

## Completion expectations
- Implementation
- Every requirement in a parsed `RequirementMap` carries one of the three
  dispositions.
- A response with a `yielded` disposition and no obligation ids is rejected.
- A response with a `no_obligation` disposition and an empty reason is rejected.
- A response omitting a requirement present in the registry is rejected.
- No `RequirementMap` is produced from a rejected response.
- The `UNDISPOSED` value and every code path that assigns it are removed.
- A response naming a requirement id outside the registry is rejected.
- A response disposing the same requirement twice is rejected.
- An `open_question` disposition naming no question the response produced is
  rejected.
- A test asserts that the schema sent to the model rejects a `yielded`
  disposition carrying zero obligation ids.
- A test asserts that the id constraint still reaches every member of a union
  item type.
- The tests, CLI rendering and report sections that referred to the removed
  disposition are updated rather than left asserting it.
- `docs/DR-202-decomposition-requirement-mapping.md` records that the
  disposition set is the three of decision 3, and that completeness is enforced
  at parse.
