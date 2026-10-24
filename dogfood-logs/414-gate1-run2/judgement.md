# 414 Gate 1 run 2 — judgement

Run `f5cc026820bcc6ee`, continuing `80fb35e8d30f29c2`. Claude Sonnet 5.5, $0.52.
10 requirements, 26 obligations, 0 open questions.

**Every specific requirement is present and accurate. The defect is duplication,
and the task file authored it.** The opening sentence (task-01) summarises the
whole task, so its five obligations restate the specific ones below:

- `claude-reuse-cached-prompt-openings` = `pair-mapping-shared-opening-cache-reads`
  / `sonnet-5-5-cache-reads-reported`
- `batch-api-routing` = `batch-api-opt-in`
- `immediate-runs-stay-synchronous` = `batch-api-off-by-default`
- `batch-results-returned-to-calls` is the only one with new content (results
  matched back to their calls), and it is implied by `batched-recording-replays-offline`
  plus the run completing.

Smaller overlap from my wording in task-02: `short-prefix-not-cached` restates
`min-reusable-prefix-512-tokens` plus `module-doc-no-rejection-claim`, because
the sentence described the provider's behaviour as if it were ours.

Linking did not merge the task-01 duplicates. I am not attributing that to the
tool yet: CLAUDE.md's ticket-grade rule says each requirement is said once,
and this file said it twice. If duplicates remain after the rewrite, revisit.

Triage: fix the task file — drop the summary sentence, reword task-02's
documentation sentence. Re-run with `--continue f5cc026820bcc6ee`.
