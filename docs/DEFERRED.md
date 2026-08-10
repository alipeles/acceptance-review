# The bundled queue

Things found mid-iteration that were deliberately not acted on at the time.
Claude queues here instead of interrupting; the queue is presented at the next
gate and worked with `/triage`. See `CLAUDE.md` *Working agreement* §4.

Resolved entries are deleted. Anything filed lives on GitHub, which is
authoritative (#168), so keeping a second copy here only costs context; an
entry resolved without a filing is recorded in the commit that resolved it.

Kind: `defect` (a bug, smell, missing test, spec inconsistency, dependency
problem, outside the current task's scope) · `filing` (a drafted issue,
sub-issue, or comment asserting a new finding — nothing reaches GitHub until
approved at a gate) · `decision` (an open design decision, with the
recommendation and the alternative rejected).

Severity: `blocker` (an Acceptance item of the task in flight depends on it) ·
`should-fix` (real defect, no Acceptance item blocked) ·
`nice-to-have` (cleanup, ergonomics, docs).

---

<!-- Template — copy, don't edit:

### [YYYY-MM-DD] <one-line title>
- **Kind:** defect | filing | decision
- **Found during:** #144, Gate 1
- **Where:** src/acceptance/requirement/obligations.py:118
- **Severity:** blocker | should-fix | nice-to-have
- **What's wrong:** one or two concrete sentences.
- **Why I didn't act:** out of scope for #144 / would change the review-state schema.
- **Drafted fix:** for a defect, what you would do — specific enough to approve or
  reject without a follow-up, with the diff sketch if it is small. For a filing, the
  issue body as it would be filed, its labels, and its parent umbrella.
- **Status:** open

-->
### [2026-08-09] A missing transcript is reported as "a prompt was probably edited"

- **Kind:** filing
- **Found during:** #232/#219/#230 bundle, Gate 2
- **Where:** `src/acceptance/llm.py` — the `TranscriptNotFoundError` message
- **Severity:** nice-to-have
- **What's wrong:** The error names one cause and recommends acting on it:
  *"the most likely cause is that a prompt was edited and has not been
  re-verified… Re-record and confirm the assertions still hold."* At Gate 2 the
  cause was something else entirely — `check` had reviewed its own redirected
  output file, so the change set differed between the record run and the replay.
  Following the message would have re-recorded the whole corpus for nothing.
  A prompt edit is *a* cause, not *the* cause; anything that alters the request
  produces the same miss.
- **Why I didn't act:** the collision that produced it is fixed
  (`.acceptance/ignore`, verified in `dogfood-logs/232-gate2-run3/`), so this is
  only the diagnostic, and it needs a call on where it belongs.
- **Drafted fix:** Reword to state the invariant rather than a guess — the request
  key hashes prompt, model, seed **and the inputs the stage was given**, so list
  those and let the reader identify which moved. Mention the prompt-edit case as
  one example rather than the conclusion. Needs a parent: **#184** (determinism &
  reproducibility) is the closest fit since the request key is its surface.
  Labels: `track:checker`.
- **Status:** open
