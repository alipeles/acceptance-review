# Task
Make the model requests of a single review run share their opening text. Content
that several of a run's requests carry is written the same way in each of them
and placed at the front, ahead of the content that is unique to the request. Where
a provider must be told where the reusable opening ends, the client tells it, and
no individual request does.

## Constraints
- Content carried by more than one of a run's requests is byte-identical in each
  request that carries it.
- Each request orders its content by how widely that content is shared across the
  run's requests: content carried by more of them precedes content carried by
  fewer, and content carried by that request alone comes last.
- Two requests of one run that share content share it as a leading run of bytes,
  not as a fragment somewhere inside them.
- Reordering a request changes only the order of what it carries; it carries the
  same content afterwards as before.
- Where a provider must be told where a request's reusable opening ends, the
  client marks it and no request-building code does.
- The client does not mark a reusable opening shorter than the shortest one the
  provider in use can reuse.

## Scope exclusions
- What any stage is asked, and what content any stage receives. This task changes
  the order and the wording of content already carried, and adds none.
- Which stages exist, how a stage divides its work across calls, and how large
  those divisions are.
- Model calls issued by the measurement harness, which is not part of a review
  run.
- Whether a provider in fact reuses any part of a request it was offered, which
  is the provider's own behavior and not this tool's.
- Reporting tokens, cost or reused-token share, which a run already reports.
- What a token costs.

## Completion expectations
- Implementation
- A test fails when a request places content unique to it ahead of content it
  shares with another request of the same run.
- A test fails when content carried by two of a run's requests is written
  differently in the two.
- A test fails when a request built by a stage marks the end of its own reusable
  opening.
- Two recorded runs over the same input produce byte-identical review state and
  byte-identical report output.
