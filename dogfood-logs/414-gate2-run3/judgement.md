# #414 Gate 2 run 3 — not clean; owner accepted it as not clean

Run `6da616d2ddf3c443`, continuing run 2 `d0af3f8ef57c6bb9`, head 545e9e1.
Verdict INCOMPLETE: 4 of 16 obligations partially supported, one unrequested
change rated `risky`. Spent $2.3234 (Gate 2 total over three runs: $13.39).

The owner decided, 2026-10-25, to stop iterating: fix the real findings, queue
the tool defects, and decide at the PR whether to merge with Gate 2 not clean.
This was asked under the "failed the same way twice" rule: three consecutive
runs flagged the in-flight limit for batched runs as an unrequested, risky
change, against three different designs (module state; a `run_review` wrapper;
each stage passing its client's limit).

## Triage

- **4 batch-api-opt-in** (3 of 4). The instability experiment's comparison
  client never got a batcher. Real. Fixed in 4d6a93a, with a test. Its other
  claim, that a client built some other way gets no batcher, is true by design:
  `RunConfig` is the setting's only route, as the task file says.
- **5 batch-setting-in-run-configuration** (1 of 3). A `model_copy` of a
  `RunConfig` shared the original's batcher when made after the first client,
  and not when made before. Real, and introduced by run 2's fix. Fixed in
  4d6a93a: a copy always gets its own; tested both orders.
- **8 batch-opt-in-switchable-by-scripts** (3 of 5). Other benchmark paths
  cannot pass `batch`. They take a `RunConfig`, which carries it; the scoring
  path is tested (`test_benchmark_scoring_batches_when_its_configuration_says_to`).
  No change.
- **11 recording-notes-batch-origin** (2 of 3). The enumerated defect says a
  call that really went through a batch under another route or completion
  function would get no note. It cannot: one flag, `batched`, decides both
  whether the batch transport is used and whether the note is written, so no
  call is batched without the note. **Tool defect** — queued as a filing.
- **6 and 9** read `no plausible defect`, where run 2 rated both strongly
  supported (5 of 5 and 3 of 3 killed); `llm.py` and the `batch` default did not change between the runs. **Tool defect** —
  queued as a comment on #180.
- **Unrequested change 2 [risky]**: each stage passing `client.calls_in_flight`.
  Kept. Without it a batched stage goes out eight calls per batch. Queued for
  the owner as a filing, with the two earlier runs' versions of the same flag.
- **Unrequested change 7** says `message_text` is "not imported or defined in
  this diff". It is defined in `tests/support.py` on main, which the diff only
  calls; a misreading, noted here and not filed.
