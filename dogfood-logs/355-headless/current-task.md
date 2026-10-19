# Task

When decomposition finds a span of the opening summary uncovered by the
obligations already derived, and the follow-up call asked about that span alone
returns neither an obligation nor an open question, the decomposition completes
instead of stopping. The disagreement between the two steps is recorded as an
open question on the summary requirement: it says that the two steps disagreed
and quotes the span, and it links to the span's text in the task file. The rest
of the decomposition, including every other span and requirement, is derived as
usual.

A regression test is part of the deliverable: a replayed decomposition in which
the follow-up call for an uncovered span yields nothing completes, and its
result carries an open question quoting that span.

## Scope exclusions

- Do not change any prompt or response schema.
- The other refusals in the summary step (a span that is not part of the
  summary, a span decided more than once or not at all, a verdict that
  disagrees with its own counterexample) keep stopping the run.
