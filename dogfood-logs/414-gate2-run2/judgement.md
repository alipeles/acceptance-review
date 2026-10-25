# #414 Gate 2 run 2 — not clean

Run `d0af3f8ef57c6bb9`, continuing Gate 1 run 6 `b4a84b5d7ad8a84c`, on the
branch rebased onto #385 (bbda8a0). Verdict INCOMPLETE: 3 of 16 obligations
partially supported, each with a recommended test; 5 unrequested changes, two
rated `risky`. Spent $2.9759 on 1,812 live calls, inside the $2.50–4 estimate.
Every other obligation is strongly supported or owed no test.

## Triage

All findings addressed in 66210e7.

- **5 batch-setting-in-run-configuration** and **8
  batch-opt-in-switchable-by-scripts** (3 of 5, 4 of 6). Same finding twice:
  `build_client` made a new `MessageBatcher` each time, so a script building
  two clients from one configuration sent their calls in separate batches.
  Real. Addressed: `RunConfig` holds one batcher and every client it builds
  shares it; tested with two clients' calls landing in one batch.
- **11 recording-notes-batch-origin** (3 of 4). `run_once` given a
  `client_factory` that ignores the configuration's `batch` field sends
  directly. That is the factory's choice and stays so; what was untested is the
  path with no factory. Addressed: a test that `run_once`'s own client batches
  when asked and not otherwise.
- **Unrequested change 2 [risky]** (the run-wide concurrency limit held in
  module state) and **3 [risky]** (the `run_review` wrapper that found the
  client with `inspect`). Real: two reviews in one process would share the
  module state. Addressed by removing both. Each stage now passes its own
  client's `calls_in_flight` to `map_calls`, which is `None` (the default of
  eight) unless the client batches. Tested by a scan that every `map_calls`
  call in `src/acceptance/` passes it, apart from the mutation runner (sized
  for CPUs) and Jev's calls (not Claude, never batched), and by a twenty-
  requirement decomposition running more than eight calls at once for a
  batching client and at most eight otherwise.
- Unrequested changes 1, 4 and 5 are `in_service`: the full minimum table, the
  half-price cost, and `batch` on the instability functions.

## Process

Defect injection: a stage dropping its client's limit, each client getting its
own batcher, and decomposition dropping its limit each made a new test fail.
