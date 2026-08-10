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

### [2026-08-10] A mapped test set collapsed from two tests to zero across an additive diff
- **Kind:** filing (comment on #180, cross-referencing #182)
- **Found during:** #214, Gate 2 runs 1 and 2
- **Where:** `dogfood-logs/214-gate2-run1/`, `dogfood-logs/214-gate2-run2/`
- **Severity:** blocker (it is why #214's Gate 2 is not clean)
- **What's wrong:** two Gate 2 runs whose heads differ by **three added tests and
  no source change** disagreed about 7 of 21 obligations. Four ratings fell. The
  cleanest case: `constraint-11` ("Tests issue no live model calls") was
  `strongly supported` in run 1 citing two mapped tests, and `unsupported` with
  **`(no mapped test)`** in run 2. Both tests still exist and neither was touched.
- **Why I didn't act:** it is a defect in the checker's own mapping and judgement
  stages, not in #214's change. Chasing it by writing more tests is what #180
  warns cannot work — a gate that names a different set each run cannot be
  converged on by fixing what it names.
- **Drafted fix — comment to post on #180:**

  > **A cleaner reproduction than the corpus currently holds: a mapped set going from two tests to zero.**
  >
  > From #214's Gate 2, two runs over the same task file. The heads differ by
  > **three added tests and no source change** (`be4367d` → `bb1f1ef`). 7 of 21
  > obligations moved rating; four fell.
  >
  > ```
  > completion-09   strongly supported -> partially supported
  > completion-10   strongly supported -> partially supported
  > constraint-09   strongly supported -> nominally supported
  > constraint-11   strongly supported -> unsupported   (no mapped test at all)
  > ```
  >
  > `constraint-11` is the one worth keeping. In run 1 it cited:
  >
  > ```
  > tests/benchmark/test_coverage.py::test_cli_and_benchmark_share_one_pipeline
  > tests/coverage/test_open_questions.py::test_no_open_questions_issues_no_model_call
  > ```
  >
  > Both still exist, neither was touched between the heads, and run 2 reports
  > `(no mapped test)`. **The mapped set collapsed from two to zero with no change
  > to the tests.** This is stronger than the `remove-stale-next-instruction-file`
  > case in the corpus: there the rating moved while the mapped set survived, so
  > mapping and judgement were confounded. Here the judgement had nothing to
  > judge — mapping alone accounts for it, which separates the two layers this
  > issue and #182 deliberately keep apart.
  >
  > **Checked against this issue's corrected reading before filing.** #180 says a
  > falling rating is usually the judge finally noticing a real hole, and that
  > inference must not be skipped. I read all four recommendations:
  >
  > - `constraint-09` asks for a test using "a model client that would fail if
  >   consulted" — but `derive_verdict` takes no client parameter, so its
  >   signature already guarantees what the recommendation asks a test to show.
  > - `completion-09` asks for an assertion inspecting `run_review`'s completion
  >   with all three dispositions present. That test exists, and **the same run
  >   cites it as evidence for the obligation it says lacks it**.
  > - `completion-10` asks for a fixture containing a resolved open question and
  >   a declined requirement. The fixture has both.
  > - `constraint-11` has no mapped test to reason about.
  >
  > So unlike the run-3 findings recorded above, these are not pre-existing holes
  > the judge finally saw. Three describe tests that exist; one lost its mapping.
  >
  > Both runs' inputs, outputs and judgements are committed at
  > `dogfood-logs/214-gate2-run1/` and `-run2/`, in the shape that can become a
  > benchmark case.
- **Status:** open
