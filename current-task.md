# Task
Make the model harness genuinely provider-agnostic. Calls route through LiteLLM
so the model can be swapped to compare quality and cost, but a run against a
non-OpenAI model currently fails before it reaches the model, and the schema the
harness sends hides its enum values behind a reference, which changes the
answers the model gives. Have LiteLLM perform the per-provider translation,
send schemas with their values inline, record which determinism controls the
provider actually honoured, and hold the whole claim to recorded evidence
rather than a hand-run experiment.

## Constraints
- A completion function injected by a caller must not pull in the provider stack, so capability tests keep running with no provider dependency.
- The schema sent to the provider must also be the schema inside the hashed request, so a change to how schemas are rendered invalidates recordings instead of replaying judgments made under a different schema.

## Scope exclusions
- Carrying the provider-honoured determinism controls through into the review's own provenance is deferred to a follow-up; this change records them in the transcript only.

## Completion expectations
- Implementation
- A live call against a provider that rejects a configured determinism control still reaches the model instead of raising first.
- The structured-output request is expressed through LiteLLM's own response-format interface, so LiteLLM translates it into each provider's native mechanism instead of the harness targeting one provider's API directly.
- The schema sent to the provider carries its enum values inline, with no `$defs` or `$ref` indirection, because that indirection changes the model's answer.
- Every recorded transcript states which determinism controls actually applied, and a control the provider discarded reads as not in force rather than as the value requested.
- The recorded corpus holds transcripts from more than one provider, drawn from a declared set of approved models, so provider-agnosticism rests on recorded evidence like every other capability.
- A requirement span locates its text exactly, so `source[start:end]` equals the span's own text even when a bullet wraps across lines.
- The model the tool runs by default is pinned by a guard, so that swapping it becomes a deliberate and visible edit rather than a silent drift that invalidates the recorded corpus.
