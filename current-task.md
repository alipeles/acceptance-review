# Task
Open questions from decomposition are silently dropped downstream of `decompose`, and never gate the verdict. Surfaced dogfooding M4.1: `run_classify` (`cli.py`) and `classify_case` (`benchmark/coverage.py`) both call `decompose(...).obligations` — only the obligations are kept; `.open_questions` is computed and then discarded. Only `render_decomposition` (the standalone `decompose` command's renderer) ever shows open questions to a human at all.

## Constraints
- `Review`/the `classify` pipeline must carry open questions through from decomposition to CLI output, not drop them at the first `.obligations`-only call site.
- When the diff itself makes the answer to an open question clear, that must be noted and the question recorded as resolved — not shown as perpetually "unresolved" on every re-run regardless of whether the diff already answers it. When the diff doesn't answer it, it stays flagged open.
- What counts as "resolved" beyond "the diff itself makes the answer clear" is reviewer judgment; the tool's job is to make and record that specific judgment, not to build a separate manual sign-off mechanism.

## Scope exclusions
- The completion verdict itself (M7.2, #33) — whether an unresolved open question blocks a `no-material-gaps` result — is out of scope for this task; that milestone hasn't been reached yet in the plan sequence. #33's own scope has already been updated separately (outside this diff) to carry that requirement forward.

## Completion expectations
- Implementation: open questions threaded through `Review`, `run_classify`, and `classify_case`; a judgment step decides, per open question, whether the diff resolves it, and records that judgment (not just displays it transiently); `classify`'s CLI output shows resolved questions (with the answer and its source) separately from still-open ones.
- Unit tests: resolved and still-open cases, including a question the model doesn't return a judgment for (must stay open, not vanish); existing coverage/disposition/CLI tests unaffected.
