# #398 Gate 1, run 1 — judgement

Run `9c80499269145c8d`, `acceptance decompose --task current-task.md`, on branch
`398-load-dotenv` off main 80511ee. The first attempt wrote a zero-byte
`output.log` (the known CLAUDE.md failure); this log is the identical re-run,
which replayed the first attempt's recordings.

14 obligations, 0 open questions. Not accepted; the task file was reworded.

## Findings

All three are attributed to my wording of `current-task.md`, not to the tool.

- **Duplicate pair from a topic sentence.** task-03 opens with "A missing key
  must be reported clearly and early, never as the provider's 'invalid API key'
  reply", which only summarises the sentences after it. It yielded two
  near-identical obligations, `missing-key-reported-clearly-and-early` and
  `clear-missing-key-reporting`, both restating what
  `record-mode-warns-missing-model-keys-at-startup` and
  `missing-key-stops-before-live-call` say concretely. Fix: drop the topic
  sentence and attach "not the provider's invalid-key reply" to the stop.
  The two obligations are near-verbatim and were not linked as duplicates; that
  is worth watching, but the cause is a sentence that should not exist, so no
  filing.
- **Outcome paragraph restates the mechanism.** task-01 yielded
  `load-provider-keys-from-cwd-env`, the same behaviour as
  `load-env-before-model-call` from task-02. Fix: fold the outcome into one
  requirement and keep the "why" as a single non-normative sentence.
- **Exclusion read as a prohibition.** "Keys for the coding agent that builds
  mutation edits" became `do-not-read-coding-agent-keys`. What I meant is that
  *checking for* that agent's keys is out of scope. Fix: say that.

## Correct

`preserve-existing-env-vars`, `no-dotenv-file-is-not-an-error`,
`record-mode-warns-missing-model-keys-at-startup`,
`missing-key-stops-before-live-call`, `call-not-sent`,
`no-live-call-no-keys-required`, `preserve-recorded-transcripts-replay`, and the
other two exclusions.
