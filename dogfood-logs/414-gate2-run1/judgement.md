# #414 Gate 2 run 1 — not clean

Run `3ae1a86e857c8a45`, continuing Gate 1 run 5 `b1b2749ff056bea4`. Verdict
INCOMPLETE: 8 of 16 obligations only partially supported by test evidence, each
with a recommended test; 9 unrequested changes, one rated `risky`. Spent $8.0876
on 789 live calls, above the $3–6 estimated beforehand; the pair mapping stage
alone was $6.16 over 722 calls.

**Acceptance item 2 is shown here.** The pair mapping stage read 14.9% of its
prompt tokens from the cache, and the mutation descriptor 11.9%. #413's Gate 2
read 0.0% on every stage.

## Triage, by obligation

Every negative finding was addressed in the code or the task file (19a8b17 and
the task-04 rewording), except obligation 3's, which is removed with its stage.

- **1 min-reusable-prefix-per-model** (1 of 3 killed). The surviving defects
  were model names in other routes' forms (`bedrock/anthropic.claude-…`,
  `vertex_ai/claude-…`) reaching the wrong minimum. Real, though unreachable
  today because only `anthropic/` names are marked. Addressed: the lookup now
  reads the name from `claude-` onward whatever the route, with those forms
  tested. The boundary defect (exactly 512 tokens) was already killed: the
  comparison is inclusive.
- **3 pair-mapping-cache-hit-on-shared-opening** (4 of 5). Surviving defect:
  followers in a batched run landing in the leaders' batch. No action: #385
  removes this stage, it merges first, and #414 drops its pair-mapping change
  and rewrites task-02 when it rebases.
- **5 batch-api-opt-in** (3 of 5). The `run_review` wrapper finding a client
  passed positionally, or a client with no `calls_in_flight`. Addressed: the
  wrapper reads the attribute with a default; tests for positional, keyword
  and default-limit clients.
- **6, 8** (5 of 6 each). Non-Claude stages and embeddings go directly in a
  batched run. True and by design: the Message Batches API carries Claude
  completions only. The task file said "its model calls"; that was my wording
  and it was wrong. Reworded to "its calls to Claude models". An embedding in a
  batched run is now tested to go direct with no batch note.
- **7 check-and-decompose-call-model-directly-by-default** (4 of 5). Addressed:
  a test that a default client, on the real LiteLLM path, posts directly and
  creates no batch.
- **11 recording-notes-batch-origin** (3 of 4). A note claiming "batch" on a
  call that was not batched. Real for an injected completion function, which
  received the batch transport and ignored it. Addressed: batching now applies
  only on the real LiteLLM path; tests for an injected function and for a
  batched call answered on a retry.
- **12 identical-review-state-across-send-modes** (3 of 4). Addressed: the
  whole pipeline recorded once each way into one transcript root, through the
  real provider path, produces byte-identical review state.

## Unrequested changes

Eight are `in_service`. The `risky` one is the `run_review` wrapper, which
binds arguments with `inspect` to find the client. Kept, because the in-flight
limit has to be set before any stage builds its thread pool and `run_review` is
the one entry point both consumers share; hardened as described under 5.

## Process

Defect injection on the fixes: the old name lookup, batching through an
injected function, and the wrapper reading only keyword arguments each made a
new test fail.
