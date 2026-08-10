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

### [2026-08-10] `ruff check .` reports 85 pre-existing errors

- **Kind:** defect
- **Found during:** #234, Gate 2 preparation
- **Where:** repo-wide — `benchmark/case.py`, `benchmark/instability.py`,
  `benchmark/scoring.py`, `cli.py`, `rerun.py`, `review_state.py` and others
- **Severity:** should-fix
- **What's wrong:** `.venv/bin/ruff check .` — the command CLAUDE.md documents as
  "lint, as CI runs it" — exits 1 with 85 errors on an otherwise untouched tree.
  None come from #234's changes: only `benchmark/fixtures.py` and
  `tests/benchmark/test_fixtures.py` are modified, and the single hit inside them
  is on pre-existing code. Installed ruff is 0.16.2, which enforces rules
  (`UP037`, `RUF022`, `I001`, `PLW1510`) the tree was last clean against under an
  older version; `pyproject.toml` pins no ruff version and selects no rule set.
  CI's lint step is `ruff check . || echo "ruff not configured yet — skipping"`,
  so it stays green and the drift is invisible there.
- **Why I didn't act:** 85 errors across nine modules is a diff far larger than
  #234, and it would bury the two-line fix under unrelated churn.
- **Drafted fix:** one commit of `ruff check --fix .` for the 56 mechanically
  fixable ones, hand-fix the rest, then pin ruff in `[project.optional-dependencies]`
  and drop the `|| echo` from `ci.yml` step 4 so lint blocks again. That last part
  is the load-bearing half — without it the tree drifts back.
- **Status:** open

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
