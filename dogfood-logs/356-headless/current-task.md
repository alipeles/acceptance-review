# Task: Retry transient provider failures on live model calls

## Task

Live provider calls, both completion and embedding, retry transient failures
before giving up. A transient failure is a connection error, a timeout, a
server error (5xx) or a rate-limit response (429). The retries are bounded in
number and wait with backoff between attempts.

A retry leaves no trace in what is recorded. Only a successful response is
persisted, so a call that failed transiently once and then succeeded produces
the same transcript, under the same request key, as a call that succeeded on
its first attempt, and replay serves it the same way.

A call that is still failing once the retries are exhausted, or that fails with
a provider error that is not transient, raises `LLMError`. Its message names the
stage the call was made for, the provider or model, and the status, and fits on
one line, so the command line reports it as a single `acceptance: model error:`
line.

A regression test is part of the deliverable: a completion call and an
embedding call whose provider fails transiently once and then succeeds, each
shown to record exactly what a first-time success records, and a call that keeps
failing shown to surface as one `acceptance: model error:` line naming the
stage.

## Constraints

- Retrying is not part of a request's identity: nothing about the retry
  policy enters the request key, so every existing recording replays.

## Scope exclusions

- Replay mode makes no provider calls, so it has nothing to retry.
- Failures that are not provider errors, such as a response that fails schema
  validation, are not retried.
