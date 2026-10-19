# Declaration — #355

Written from memory of the work, before reading the diff.

## What I implemented

In `src/acceptance/requirement/obligations.py`, the summary step's loop over
uncovered spans no longer raises `SchemaValidationError` when the call asked
about one span alone yields neither an obligation nor an open question. It now
calls a new helper, `_span_disagreement`, which mints an `OpenQuestion` with id
`<summary id>-span-<nn>-disagreement` (uniqued against the run's ids), whose
text says the coverage step and the span's own call disagreed and quotes the
span, and whose `source_spans` is the span's own offsets in the mandate. Its id
goes into the summary's `open_question_ids`, so the summary's disposition becomes
`open_question` when no other span yielded an obligation, or stays `yielded`
with the question attached when one did. Every other span and requirement is
derived as before.

The question text is written by code, not asked of the model. No prompt or
response schema changed.

## What I tested

Replaced `test_an_uncovered_span_that_yields_nothing_stops_the_run` in
`tests/requirement/test_summary_pass.py` (it pinned the abort the issue calls
the bug) with
`test_an_uncovered_span_that_yields_nothing_becomes_an_open_question`. It
replays a decomposition in which the uncovered span's call answers
`no_obligation`, and asserts: the run completes; the bullet's obligation
`header-row` is still derived; `task-01`'s disposition is `open_question`; the
question quotes the span and says "disagreed"; its source span is the span's
exact text at the right offsets. I saw it fail with the issue's error before
the fix and pass after.

The other refusals in that file (span not a substring, decided twice or not at
all, verdict contradicting its counterexample) still pass unchanged, so they
still stop the run.

## What I left out

- The same path is reached when the span call's answer is unusable (its
  `requirement_disposition` rejected by `_usable_disposition`). That case now
  also becomes a disagreement question rather than an abort. I did not write a
  separate test for it.
- If the span call returned open questions but a `no_obligation` disposition,
  those questions are recorded in the run's list but are not linked to the
  summary; that was already so before the fix and I did not change it.

## Assumptions

- `importance` stays the default `normal`.
- Linking the question to the summary requirement (not a separate span
  requirement disposition) is what "an open question on its requirement" means.

## Unverified

- I have not seen the fix work on a live recording; the decompose run of this
  task file crashed with the very error being fixed, because it ran the
  unfixed code.
- 11 benchmark tests fail locally because the tag `corpus/163-gate2-run1` is
  not on origin. I believe that is unrelated to this change (see notes.md).
