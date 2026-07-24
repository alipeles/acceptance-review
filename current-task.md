# Task
Open questions from decomposition are silently dropped downstream of `decompose`, and never gate the verdict. Surfaced dogfooding M4.1: `run_classify` (`cli.py`) and `classify_case` (`benchmark/coverage.py`) both call `decompose(...).obligations` — only the obligations are kept; `.open_questions` is computed and then discarded. Only `render_decomposition` (the standalone `decompose` command's renderer) ever shows open questions to a human at all. This connects to two CLAUDE.md invariants: "Uncertainty is first-class" (open questions are a valid, expected output, not something to quietly discard) and "Positive results are bounded" (a review can't honestly report "no material gaps" while an open question about what the obligation even means remains unresolved).

## Constraints
- Nearer-term / smaller scope for this task: `Review`/the `classify` pipeline must carry `open_questions` through from decomposition to CLI output, not drop them at the first `.obligations`-only call site — even before M7's verdict machinery exists.
- The completion verdict itself (M7.2, #33) is out of scope here — that milestone hasn't been reached yet in the plan sequence. Instead, #33's own scope must be updated to explicitly name unresolved open questions as blocking a `no-material-gaps` verdict, so the requirement isn't lost when M7.2 is eventually built.
- What "resolved" means mechanically is a reviewer/human judgment call made by reading whether the diff answers the question — not a new mechanism this task needs to build or a formal decision record; that judgment is deferred to whoever reads the review (or a future M7.2 capability), not decided here.

## Completion expectations
- Implementation: `open_questions` threaded through `Review`, `run_classify`, and `classify_case`; `classify`'s CLI output (`render_classify`) shows open questions the same way `decompose`'s does.
- Unit tests: rendering with and without open questions; existing coverage/disposition/CLI tests unaffected.
- #33 updated to explicitly scope in the open_questions -> verdict wiring for when M7.2 lands.
