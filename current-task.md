## Deliverable
a thin layer that issues schema-constrained model calls, validates responses against the target schema, and records every prompt/response for replay.

## Acceptance
a recorded transcript replays a full run with zero live model calls; a malformed model response is rejected with a typed error, not silently accepted.
