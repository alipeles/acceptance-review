# #355 Two decomposition calls disagreeing about one span abort the whole decomposition

When the coverage step judges a span of a requirement uncovered and the follow-up call about that span alone yields neither an obligation nor an open question, `requirement/obligations.py` (the raise at about line 1161) throws `SchemaValidationError`, and `decompose` — and any review — exits with nothing. Observed at #348's Gate 1, `dogfood-logs/348-gate1-run1/`, on the span "exactly as today":

> span 1 of requirement 'task-03' was found uncovered by the obligations already derived, but the call asked about it alone produced neither an obligation nor an open question: 'exactly as today'

The two calls contradict each other, and that is information, not an error: either the span has no content of its own (the follow-up is right) or the follow-up missed a property (the coverage step is right). Neither answer justifies destroying the run. The raise exists so an uncovered property is not lost silently, which is right; losing the whole run is the other extreme. Same shape as the closed #266, where one weak obligation aborted a whole review.

## Deliverable

The contradiction is recorded, never raised. The span becomes an open question on its requirement stating that the two steps disagreed and quoting the span, so the property is surfaced rather than lost, and the rest of the decomposition completes.

## Acceptance

A replayed decomposition in which the span call yields nothing completes, and carries an open question quoting the span.
