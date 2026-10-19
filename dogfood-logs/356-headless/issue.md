# #356 One transient provider error aborts a whole review

`llm.py` retries nothing. A 502, a timeout or a rate-limit response from any provider, on any of a review's ~500 calls, raises out of the pipeline and discards the run; the CLI prints a raw traceback because provider exceptions are not converted to `LLMError`. Observed at #348's Gate 2 (`dogfood-logs/348-gate2-run2/output-attempt1-502.log`): a Voyage 502 in pair ranking, after enumeration and all injected-edit test runs had completed.

Recording is per call, so a rerun replays what finished and the money lost is small (the rerun replayed 74 calls). The time is not, and neither is the reliability: the chance a review survives falls with every call it makes. #348 added several embedding requests per review, so the exposure has grown.

## Deliverable

Live provider calls — completion and embedding — retry transient failures (connection errors, 5xx, 429) with bounded backoff before failing, and a call that still fails raises `LLMError` naming the stage, the provider and the status, so the CLI reports it in one line. A retry changes nothing that is recorded: only a successful response is persisted, as now, so request keys and replay are unaffected.

## Acceptance

A completion and an embedding call whose provider fails transiently once and then succeeds are recorded exactly as a call that succeeded first time; one that keeps failing surfaces as a single-line `acceptance: model error:` naming the stage.
