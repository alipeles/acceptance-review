# 412 Gate 1, run 1 — judgement

Run `7744c16d7cd1f3ed`, `decompose` on main at 5f841e0, default models
(`openai/gpt-5.4-mini`, `openai/gpt-5.4` for the summary-span stage). Task file is
ticket grade, written for slice 1 of #412 (point the harness at Claude).

18 obligations from 10 requirements, 0 open questions. Not accepted; reworded and
re-run as run 2.

## Findings

1. **`model-calls-move-to-claude`** — real, my wording. The opening sentence "Model
   calls move from OpenAI to Claude" was a summary of the sentence after it and
   became its own obligation. Fixed by deleting the sentence.
2. **`claude-accepts-neither-seed-nor-temperature`** and
   **`recorded-transcripts-reproducibility`** — real, my wording. The premise
   "Claude accepts neither a seed nor a temperature, so a run against it is
   reproducible only through its recorded transcripts" states a fact about the
   provider, which no code change can satisfy. Fixed by moving that fact into the
   documentation requirement it justifies.
3. **`provenance-records-claude-applied-neither` marked `code_only`** — tool defect.
   What the review's provenance records is runtime output that a test can show; the
   stated reason ("settled by the recorded output itself") is the argument for a
   test, not against one. Matches open #374 (a testable behaviour of the delivered
   code is ruled "test evidence not required"). Recorded against #374; a comment
   adding this example is drafted in `docs/DEFERRED.md`. Run 2 classified the same
   obligation `code_and_tests`, so the classification is also unstable.
