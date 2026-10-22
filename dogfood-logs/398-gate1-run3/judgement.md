# #398 Gate 1, run 3 — judgement

Run `c39bcc784e81e9ad`, `acceptance decompose --task current-task.md --continue
744ba51d41556fba`, on branch `398-load-dotenv` off main 80511ee. The first
attempt wrote a zero-byte `output.log` for the third time in this gate, again
on the attempt that made live calls; this log is the replaying re-run.

11 obligations, 0 open questions.

## Findings

- **Wording fix landed.** The duplicate pair from run 2 is now one obligation,
  `env-vars-take-precedence`.
- **Tool defect, carried from run 2:** `startup-warns-missing-model-keys` still
  lacks "in record mode". task-02 was not edited, so it was carried, as #269's
  carry-forward rule intends.
- **Tool defect: a reworded exclusion keeps its old, false obligation.**
  exclusion-02 now reads *"Warning about, or stopping for, a missing key that
  the coding agent which builds mutation edits needs"*, its second rewording,
  and still yields `do-not-read-coding-agent-keys`, word for word: *"The change
  does not read keys for the coding agent which builds mutation edits."* Two
  rewordings, the same text each time, so this is not my wording. Run 4, a
  fresh run on this byte-identical file, derives the right obligation. Second
  instance of the drafted, unfiled 2026-09-22 queue entry "A revised requirement
  comes back with its old obligation, word for word"; evidence added to the
  queue.
