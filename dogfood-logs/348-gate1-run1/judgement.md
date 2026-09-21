# #348 Gate 1, run 1 — aborted

`acceptance decompose` exited 1 without producing an obligation set:

> span 1 of requirement 'task-03' was found uncovered by the obligations already
> derived, but the call asked about it alone produced neither an obligation nor
> an open question: 'exactly as today'

## What the span was

`task-03` is the paragraph "A defect none of whose tests is recorded as catching
it has every one of its tests asked about, exactly as today." Span 1 is the
trailing "exactly as today".

## Judgement

Two things, both real.

1. **Weak wording (mine).** "Exactly as today" has no content on its own; the
   property it points at is already stated by the rest of the sentence. Fixed in
   run 2 by deleting it. This is the sanctioned rewrite of a weak requirement.
2. **Tool defect.** `requirement/obligations.py:1155` raises
   `SchemaValidationError` when the coverage step calls a span uncovered and the
   span call then yields nothing. That is two model calls contradicting each
   other, and it aborts the entire decomposition — nothing is recorded, no
   obligations, no open question. The comment says the raise exists so the
   property is not "lost silently", which is right, but losing the whole run is
   the opposite extreme. The contradiction should become an open question on the
   span (or a recorded unresolved span), not a crash. Same shape as the closed
   #266, where one weak obligation aborted a whole review. Queued as a filing
   draft against #181 (the decomposition umbrella) in `docs/DEFERRED.md`.
