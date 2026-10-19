# Declaration — #356, retry transient provider failures

## What I implemented

All in `src/acceptance/llm.py`:

- `ModelClient._call_provider(fn, kind, stage, **kwargs)`: calls the provider
  function, and on a transient failure waits and calls it again with the same
  arguments. Up to 5 attempts, waiting 2, 4, 8 and 16 seconds between them
  (at most 30 seconds of waiting per call).
- Both live paths go through it: `_live_call` (completion) and
  `_persist_live_embedding` (embedding). `_persist_live_embedding` gained a
  `stage` parameter so the error can name the stage; `embed` passes it.
- Transient means: an exception with a `status_code` of 408, 429 or 500+
  (LiteLLM's exceptions all carry one), or a builtin `ConnectionError` /
  `TimeoutError`. Status is read by attribute, so replay mode still never
  imports litellm.
- A transient failure that outlasts 5 attempts, or a provider error with a
  non-transient status (e.g. 401), raises `LLMError` whose message names the
  kind of call, the stage, the model string (which carries the provider prefix,
  e.g. `voyage/voyage-3.5-lite`), the status, and the provider's message. The
  message has its whitespace collapsed and is capped at 300 characters, so it
  is one line even when the provider returns an HTML error page.
- Exceptions that are not provider failures (no `status_code`, not a
  connection or timeout error) propagate unchanged and are not retried — so a
  bug in our code, or a test fake's `AssertionError`, is not dressed up as a
  network problem.
- Nothing about retrying enters the request, the request key, or the
  transcript. Only the successful attempt's response is recorded, by the same
  code that recorded it before.

The CLI needed no change: `decompose`, `check` and `classify` already catch
`LLMError` and print `acceptance: model error: <message>`. (`cli.py` is
reserved for another session anyway.)

## What I tested

New file `tests/test_llm_retry.py`, 14 tests:

- a completion failing once with 502, 503, 429, 408, `ConnectionError` or
  `TimeoutError`, then succeeding, writes byte-identical transcript files (same
  file names, i.e. same request keys) to a first-time success, returns the same
  answer, and sends identical arguments on both attempts;
- the same for an embedding failing once with 502;
- a retried completion replays in REPLAY mode with a provider that explodes;
- a call that always fails is attempted more than once and fewer than ten
  times, waits grow, and nothing is written to the store;
- the exhausted error is one line and names stage, model and status, for both
  a completion and an embedding;
- a 401 is attempted once and becomes `LLMError`;
- a `KeyError` is attempted once and propagates as `KeyError`;
- through `cli.main(["decompose", ...])`, an always-502 provider produces exit
  status 1 and exactly one non-empty stderr line, starting
  `acceptance: model error:` and naming `decompose` and `502`.

All 14 failed before the fix except the `KeyError` control (see `notes.md`,
Reproduction), and all pass after it. Full suite, ruff check and ruff format
check were run; see notes for the suite result.

## What I left out

- No configuration knob for the attempt count or the backoff; they are module
  constants.
- No jitter on the backoff.
- No honouring of a `Retry-After` header on 429.
- `replay_or_run` (the coding-agent path from #338) is not wrapped; the issue
  names completion and embedding calls only.
- LiteLLM's own `num_retries` is not used; the retry is ours so it is the same
  for an injected provider function and the real one.

## What I assumed

- That LiteLLM's exceptions carry `status_code`. After writing the code I
  verified it against the installed litellm 1.96.2 by constructing each class:
  `Timeout` 408, `APIConnectionError` 500, `RateLimitError` 429,
  `InternalServerError` 500, `ServiceUnavailableError` 503, `BadGatewayError`
  502, `AuthenticationError` 401. I did not provoke a real provider failure, so
  whether the Voyage path raises one of these (rather than something without a
  status) is still an assumption.
- That "the provider" in the issue is satisfied by the model string, which
  carries the provider prefix.

## What I know is unverified

- No live provider failure was exercised; every test uses a fake provider that
  raises a status-carrying exception shaped like LiteLLM's.
- The backoff timing is tested by recording the requested waits, not by real
  sleeping.
